#!/usr/bin/env python3
"""
Technical Analysis Agent — Layer 2 -> Layer 4
Python computes indicators -> DeepSeek reasons -> Pydantic validates
"""

import os, json, logging
from typing import Literal, Optional

import pandas as pd
import numpy as np
from openai import OpenAI
from pydantic import BaseModel, Field, field_validator
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), "..", "config", ".env"))

logger = logging.getLogger(__name__)


class TechnicalSignal(BaseModel):
    symbol: str
    timeframe: str
    trend: Literal["bullish", "bearish", "neutral"]
    strength: int = Field(ge=1, le=10)
    support: float = Field(gt=0)
    resistance: float = Field(gt=0)
    key_reason: str = Field(max_length=200)
    risk_score: int = Field(ge=1, le=10)
    is_volume_confirmed: bool

    @field_validator('resistance')
    def resistance_gt_support(cls, v, info):
        if 'support' in info.data and v <= info.data['support']:
            raise ValueError('resistance must be > support')
        return v


class TechIndicators:
    """Pure Python computation — LLM never touches numbers"""

    @staticmethod
    def compute(df: pd.DataFrame) -> dict:
        close = df['close'].astype(float)
        high = df['high'].astype(float)
        low = df['low'].astype(float)
        vol = df['volume'].astype(float)

        ma5 = close.rolling(5).mean().iloc[-1]
        ma20 = close.rolling(20).mean().iloc[-1]
        ma60 = close.rolling(60).mean().iloc[-1] if len(close) >= 60 else ma20

        delta = close.diff()
        gain = delta.clip(lower=0).rolling(14).mean()
        loss = (-delta.clip(upper=0)).rolling(14).mean()
        rsi = 100 - 100 / (1 + gain.iloc[-1] / (loss.iloc[-1] + 1e-9))

        tr = pd.concat([
            high - low,
            (high - close.shift()).abs(),
            (low - close.shift()).abs()
        ], axis=1).max(axis=1)
        atr = tr.rolling(14).mean().iloc[-1]

        vol_ma5 = vol.rolling(5).mean().iloc[-1]
        vol_ratio = vol.iloc[-1] / (vol_ma5 + 1e-9)

        ema12 = close.ewm(span=12).mean()
        ema26 = close.ewm(span=26).mean()
        macd = ema12.iloc[-1] - ema26.iloc[-1]
        signal_line = (ema12 - ema26).ewm(span=9).mean().iloc[-1]

        current = float(close.iloc[-1])

        return {
            "current_price": round(current, 4),
            "ma5": round(float(ma5), 4),
            "ma20": round(float(ma20), 4),
            "ma60": round(float(ma60), 4),
            "rsi14": round(float(rsi), 1),
            "atr14": round(float(atr), 4),
            "volume_ratio": round(float(vol_ratio), 2),
            "macd": round(float(macd), 6),
            "macd_signal": round(float(signal_line), 6),
            "price_above_ma20": current > float(ma20),
            "price_above_ma60": current > float(ma60),
            "golden_cross": float(ma5) > float(ma20),
            "pct_from_ma20": round((current - float(ma20)) / float(ma20) * 100, 2),
        }


class TechnicalAgent:
    def __init__(self):
        self.client = OpenAI(
            api_key=os.getenv("DEEPSEEK_API_KEY"),
            base_url=os.getenv("DEEPSEEK_BASE_URL"),
        )
        self.model = os.getenv("DEEPSEEK_MODEL", "deepseek-chat")

    def analyze(self, symbol: str, df: pd.DataFrame,
                timeframe: str = "1d") -> Optional[TechnicalSignal]:
        if df.empty or len(df) < 30:
            logger.warning(f"{symbol}: insufficient data")
            return None

        ind = TechIndicators.compute(df)

        prompt = (
            "You are a professional trading technical analyst. "
            "Analyze based on these indicators.\n\n"
            f"Symbol: {symbol} | Timeframe: {timeframe}\n"
            f"Price: {ind['current_price']}\n"
            f"MA5={ind['ma5']} MA20={ind['ma20']} MA60={ind['ma60']}\n"
            f"Golden Cross: {ind['golden_cross']} | Pct from MA20: {ind['pct_from_ma20']}%\n"
            f"RSI(14): {ind['rsi14']} | ATR(14): {ind['atr14']}\n"
            f"MACD: {ind['macd']} | Signal: {ind['macd_signal']}\n"
            f"Volume Ratio: {ind['volume_ratio']}\n\n"
            "Output JSON format:\n"
            '{"trend":"bullish/bearish/neutral","strength":1-10,'
            '"support":price,"resistance":price,"key_reason":"reason(max 200 chars)",'
            '"risk_score":1-10,"is_volume_confirmed":true/false}'
        )

        try:
            resp = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.1,
                max_tokens=500,
            )
            raw_text = resp.choices[0].message.content

            json_str = raw_text.strip()
            if '```json' in json_str:
                json_str = json_str.split('```json')[1].split('```')[0]
            elif '```' in json_str:
                json_str = json_str.split('```')[1].split('```')[0]
            result = json.loads(json_str)

            signal = TechnicalSignal(
                symbol=symbol,
                timeframe=timeframe,
                trend=result["trend"],
                strength=result["strength"],
                support=result["support"],
                resistance=result["resistance"],
                key_reason=result["key_reason"],
                risk_score=result["risk_score"],
                is_volume_confirmed=result.get("is_volume_confirmed", False),
            )
            logger.info(f"{symbol} {timeframe}: {signal.trend} (strength {signal.strength})")
            return signal

        except Exception as e:
            logger.error(f"Analysis failed {symbol}: {e}")
            return None
