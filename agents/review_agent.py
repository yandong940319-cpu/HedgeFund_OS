#!/usr/bin/env python3
"""
AI Review System — Layer 4
Post-market review: compare predictions vs actual, learn from mistakes
"""

import os, json, logging
from datetime import datetime, timedelta
from typing import Optional

import pandas as pd
from openai import OpenAI
from pydantic import BaseModel, Field
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), "..", "config", ".env"))
logger = logging.getLogger(__name__)


class ReviewResult(BaseModel):
    correct: bool
    accuracy_score: float = Field(ge=0, le=1)
    deviation: float
    lesson_learned: str = Field(max_length=500)
    adjustment: str = Field(max_length=200)


class ReviewAgent:
    def __init__(self):
        self.client = OpenAI(
            api_key=os.getenv("DEEPSEEK_API_KEY"),
            base_url=os.getenv("DEEPSEEK_BASE_URL"),
        )
        self.model = os.getenv("DEEPSEEK_MODEL", "deepseek-chat")

    def review(self, symbol: str, prediction: dict, actual_df: pd.DataFrame) -> Optional[ReviewResult]:
        """Compare prediction with actual price movement"""
        if actual_df.empty or len(actual_df) < 2:
            return None

        close = actual_df['close'].astype(float)
        actual_change = (float(close.iloc[-1]) - float(close.iloc[0])) / float(close.iloc[0]) * 100
        predicted_trend = prediction.get("trend", "neutral")

        # Determine if prediction was correct
        if predicted_trend == "bullish" and actual_change > 1:
            correct = True
        elif predicted_trend == "bearish" and actual_change < -1:
            correct = True
        elif predicted_trend == "neutral" and -1 <= actual_change <= 1:
            correct = True
        else:
            correct = False

        prompt = (
            f"Review this trading prediction:\n\n"
            f"Symbol: {symbol}\n"
            f"Predicted trend: {predicted_trend}\n"
            f"Predicted strength: {prediction.get('strength', 'N/A')}/10\n"
            f"Predicted support: {prediction.get('support', 'N/A')}\n"
            f"Predicted resistance: {prediction.get('resistance', 'N/A')}\n\n"
            f"Actual price change: {actual_change:.2f}%\n"
            f"Prediction correct: {correct}\n\n"
            f"Output JSON:\n"
            '{"accuracy_score": 0-1, "deviation": deviation_pct, '
            '"lesson_learned": "what went right/wrong(max 500 chars)", '
            '"adjustment": "how to improve(max 200 chars)"}'
        )

        try:
            resp = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.1, max_tokens=500,
            )
            result = json.loads(resp.choices[0].message.content.strip()
                                .split('```json')[-1].split('```')[0].strip())

            review = ReviewResult(
                correct=correct,
                accuracy_score=result.get("accuracy_score", 0.5),
                deviation=abs(actual_change),
                lesson_learned=result.get("lesson_learned", ""),
                adjustment=result.get("adjustment", ""),
            )
            return review
        except Exception as e:
            logger.error(f"Review failed {symbol}: {e}")
            return None
