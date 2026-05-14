#!/usr/bin/env python3
"""
Position Sizing — Layer 5
Kelly formula + volatility adjustment + hard constraints
"""

import logging
import numpy as np

logger = logging.getLogger(__name__)


def calculate_position(capital: float, price: float,
                       win_rate: float = 0.5,
                       profit_factor: float = 1.5,
                       volatility_pct: float = 2.0,
                       max_position_pct: float = 0.02) -> dict:
    """
    Calculate position size using half-Kelly with volatility adjustment.

    Args:
        capital: Total account capital
        price: Current asset price
        win_rate: Historical win rate (0-1)
        profit_factor: Gross profit / gross loss
        volatility_pct: Daily volatility as percentage
        max_position_pct: Hard cap (% of capital)

    Returns:
        {shares, capital_used, capital_pct, kelly_pct, adjustments}
    """
    # 1. Kelly formula
    loss_rate = 1 - win_rate
    if profit_factor <= 0:
        profit_factor = 1.5  # default
    kelly = win_rate - loss_rate / profit_factor

    # Half-Kelly for safety
    half_kelly = max(0, kelly * 0.5)

    # 2. Volatility adjustment
    vol_adjustment = 1.0
    if volatility_pct > 3.0:
        vol_adjustment = 0.5  # High volatility: halve position
    elif volatility_pct > 2.0:
        vol_adjustment = 0.75

    # 3. Apply hard constraints
    raw_pct = half_kelly * vol_adjustment
    final_pct = min(raw_pct, max_position_pct)

    # 4. Calculate shares
    capital_used = capital * final_pct
    shares = round(capital_used / price, 6) if price > 0 else 0

    adjustments = []
    if half_kelly < kelly:
        adjustments.append("half_kelly")
    if vol_adjustment < 1.0:
        adjustments.append(f"vol_adj_{vol_adjustment}")
    if final_pct < raw_pct:
        adjustments.append("hard_cap")

    return {
        "shares": shares,
        "capital_used": round(capital_used, 2),
        "capital_pct": round(final_pct * 100, 2),
        "kelly_pct": round(kelly * 100, 2),
        "half_kelly_pct": round(half_kelly * 100, 2),
        "adjustments": adjustments,
        "volatility_pct": volatility_pct,
    }


def check_daily_loss(daily_pnl: float, capital: float,
                     max_daily_loss_pct: float = 0.10) -> dict:
    """Check if daily loss limit is breached"""
    loss_pct = abs(daily_pnl) / capital
    if daily_pnl < 0 and loss_pct >= max_daily_loss_pct:
        return {"breach": True, "reason": f"Daily loss {loss_pct:.1%} >= {max_daily_loss_pct:.0%}",
                "action": "STOP_ALL"}
    return {"breach": False, "reason": "OK", "action": "CONTINUE"}


def check_consecutive_losses(consecutive_losses: int,
                              max_consecutive: int = 3,
                              cooldown_hours: int = 24) -> dict:
    """Check if consecutive loss limit is breached"""
    if consecutive_losses >= max_consecutive:
        return {"breach": True,
                "reason": f"{consecutive_losses} consecutive losses",
                "action": f"COOLDOWN_{cooldown_hours}H"}
    return {"breach": False, "reason": "OK", "action": "CONTINUE"}
