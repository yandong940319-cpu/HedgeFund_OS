#!/usr/bin/env python3
"""
Signal Engine — Layer 6
Fuses multiple signal sources into a single trading signal
"""

import logging
from typing import Optional
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class SignalInput(BaseModel):
    source: str
    trend: str  # bullish / bearish / neutral
    strength: int = Field(ge=1, le=10)
    weight: float = Field(ge=0, le=2)


class FusedSignal(BaseModel):
    final_trend: str
    score: float = Field(ge=0, le=10)
    action: str  # STRONG_BUY / BUY / HOLD
    confidence: float = Field(ge=0, le=1)
    details: str = Field(max_length=300)


class SignalEngine:
    """Fuses multiple signal sources with regime awareness"""

    # Regime override rules
    REGIME_RULES = {
        "bull_market": {"bullish": 1.2, "bearish": 0.5, "neutral": 0.8},
        "bear_market": {"bullish": 0.5, "bearish": 1.2, "neutral": 0.8},
        "sideways": {"bullish": 0.8, "bearish": 0.8, "neutral": 1.0},
    }

    def fuse(self, signals: list[SignalInput],
             regime: Optional[str] = None) -> FusedSignal:
        """Fuse multiple signals into one decision"""
        if not signals:
            return FusedSignal(
                final_trend="neutral", score=0, action="HOLD",
                confidence=0, details="no signals"
            )

        total_weight = 0
        weighted_scores = {"bullish": 0.0, "bearish": 0.0, "neutral": 0.0}

        for s in signals:
            w = s.weight
            regime_mult = 1.0
            if regime:
                rules = self.REGIME_RULES.get(regime, {})
                regime_mult = rules.get(s.trend, 1.0)

            weighted_scores[s.trend] += w * s.strength * regime_mult
            total_weight += w

        # Normalize to 0-10 scale
        avg_score = max(weighted_scores.values()) / (total_weight / max(len(signals), 1) + 0.001)
        score = min(10, round(avg_score, 1))

        final_trend = max(weighted_scores, key=weighted_scores.get)

        # Determine action
        if score >= 7 and final_trend != "neutral":
            action = "STRONG_BUY" if final_trend == "bullish" else "STRONG_SELL"
        elif score >= 5 and final_trend != "neutral":
            action = "BUY" if final_trend == "bullish" else "SELL"
        else:
            action = "HOLD"

        # Confidence
        total = sum(weighted_scores.values())
        top = max(weighted_scores.values())
        confidence = round(top / (total + 0.001), 3) if total > 0 else 0

        details = f"{len(signals)} signals fused | {action} | score={score} | confidence={confidence}"
        if regime:
            details += f" | regime={regime}"

        return FusedSignal(
            final_trend=final_trend,
            score=score,
            action=action,
            confidence=confidence,
            details=details,
        )

    def should_trade(self, signal: FusedSignal,
                     min_score: float = 5.0,
                     min_confidence: float = 0.5) -> bool:
        """Determine if a signal should trigger a trade"""
        return signal.score >= min_score and signal.confidence >= min_confidence
