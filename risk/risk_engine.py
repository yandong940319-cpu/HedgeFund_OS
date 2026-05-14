#!/usr/bin/env python3
"""
Risk Engine — Layer 5 (hard-coded, no LLM)
Four-layer risk control system
"""

import logging
from datetime import datetime, timedelta
from typing import Optional

from risk.position_sizing import calculate_position, check_daily_loss, check_consecutive_losses
from risk.black_swan import detect_anomaly

logger = logging.getLogger(__name__)


class RiskResult:
    def __init__(self):
        self.approved = True
        self.reject_reason = ""
        self.position_sizing = {}
        self.warnings = []


class RiskEngine:
    """Four-layer risk control"""

    def __init__(self, capital: float = 10000):
        self.capital = capital
        self.positions = []  # [{symbol, shares, entry_price, time}]
        self.daily_pnl = 0.0
        self.consecutive_losses = 0
        self.last_trade_time = None
        self.max_position_pct = 0.02  # 2% per position
        self.max_total_exposure = 0.30  # 30% total
        self.max_daily_loss_pct = 0.10  # 10% daily

    def evaluate(self, symbol: str, price: float, signal: dict,
                 df, win_rate=0.5, profit_factor=1.5,
                 volatility_pct=2.0) -> RiskResult:
        """Full risk evaluation pipeline (L1 -> L4)"""
        result = RiskResult()

        # L1: Account-level
        total_exposure = sum(p["shares"] * p["entry_price"] for p in self.positions)
        exposure_pct = total_exposure / self.capital
        if exposure_pct >= self.max_total_exposure:
            result.approved = False
            result.reject_reason = f"Total exposure {exposure_pct:.1%} >= {self.max_total_exposure:.0%}"
            return result

        daily_check = check_daily_loss(self.daily_pnl, self.capital, self.max_daily_loss_pct)
        if daily_check["breach"]:
            result.approved = False
            result.reject_reason = daily_check["reason"]
            return result

        # L2: Position-level
        cons_check = check_consecutive_losses(self.consecutive_losses)
        if cons_check["breach"]:
            result.approved = False
            result.reject_reason = cons_check["reason"]
            return result

        pos = calculate_position(
            self.capital, price, win_rate, profit_factor,
            volatility_pct, self.max_position_pct
        )
        result.position_sizing = pos

        if pos["shares"] == 0:
            result.approved = False
            result.reject_reason = "Position rounding to zero"
            return result

        # L3: Order-level checks
        if price <= 0:
            result.approved = False
            result.reject_reason = "Invalid price"
            return result

        # L4: Black swan
        anomaly = detect_anomaly(df)
        if anomaly.get("is_anomaly"):
            result.approved = False
            result.reject_reason = f"Black swan detected: {anomaly['details']}"
            return result
        if anomaly.get("anomaly_score", 0) > 0.8:
            result.warnings.append(f"High anomaly score: {anomaly['anomaly_score']:.2f}")

        return result

    def record_trade(self, symbol: str, shares: float, entry_price: float,
                     is_long: bool = True, pnl: float = 0):
        """Record a trade for risk tracking"""
        if is_long:
            self.positions.append({
                "symbol": symbol,
                "shares": shares,
                "entry_price": entry_price,
                "time": datetime.now(),
            })
        self.last_trade_time = datetime.now()

        if pnl < 0:
            self.consecutive_losses += 1
            self.daily_pnl += pnl
        else:
            self.consecutive_losses = 0
            self.daily_pnl += pnl

    def close_position(self, symbol: str):
        """Close a position by symbol"""
        self.positions = [p for p in self.positions if p["symbol"] != symbol]

    def reset_daily(self):
        """Reset daily counters"""
        self.daily_pnl = 0.0
        self.consecutive_losses = 0
