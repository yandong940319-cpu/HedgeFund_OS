#!/usr/bin/env python3
"""
Regime Detection — Layer 2 (pure Python, no LLM)
Identifies market state via MA arrangement + volatility
"""

import logging
import pandas as pd
import numpy as np

logger = logging.getLogger(__name__)


def detect_regime(df: pd.DataFrame) -> dict:
    """
    Detect market regime based on MA arrangement and volatility.
    Returns: {regime, trend_strength, volatility, description}
    """
    if df.empty or len(df) < 60:
        return {"regime": "unknown", "trend_strength": 0, "volatility": 0, "description": "insufficient data"}

    close = df['close'].astype(float)
    high = df['high'].astype(float)
    low = df['low'].astype(float)

    ma20 = close.rolling(20).mean()
    ma60 = close.rolling(60).mean()
    ma120 = close.rolling(120).mean().iloc[-1] if len(close) >= 120 else ma60.iloc[-1]

    current = float(close.iloc[-1])
    ma20_v = float(ma20.iloc[-1])
    ma60_v = float(ma60.iloc[-1])

    # MA arrangement
    if current > ma20_v > ma60_v:
        regime = "bull_market"
        strength = 3
        desc = "Bullish: price > MA20 > MA60"
    elif current > ma20_v and ma20_v < ma60_v:
        regime = "bull_recovery"
        strength = 2
        desc = "Recovering: price above MA20, MA20 still below MA60"
    elif current < ma20_v and ma20_v > ma60_v:
        regime = "bear_correction"
        strength = 1
        desc = "Correction: price below MA20, MA20 above MA60"
    elif current < ma20_v < ma60_v:
        regime = "bear_market"
        strength = 0
        desc = "Bearish: price < MA20 < MA60"
    else:
        regime = "sideways"
        strength = 1
        desc = "Sideways / mixed signals"

    # Volatility (ATR / price %)
    tr = pd.concat([
        high - low,
        (high - close.shift()).abs(),
        (low - close.shift()).abs()
    ], axis=1).max(axis=1)
    atr = float(tr.rolling(14).mean().iloc[-1])
    volatility = round(atr / current * 100, 2) if current > 0 else 0

    # Volume confirmation
    vol = df['volume'].astype(float)
    vol_ratio = float(vol.iloc[-1] / (vol.rolling(20).mean().iloc[-1] + 1e-9))

    return {
        "regime": regime,
        "trend_strength": strength,
        "volatility_pct": volatility,
        "description": desc,
        "volume_ratio": round(vol_ratio, 2),
        "price_vs_ma20": round((current - ma20_v) / ma20_v * 100, 2),
        "price_vs_ma60": round((current - ma60_v) / ma60_v * 100, 2),
    }
