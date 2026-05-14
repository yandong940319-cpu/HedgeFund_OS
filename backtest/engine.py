#!/usr/bin/env python3
"""
Backtrader Backtesting Engine — Phase 3
Tests signal engine strategies on historical data
"""

import logging
from datetime import datetime
from typing import Optional

import pandas as pd
import numpy as np

logger = logging.getLogger(__name__)


class BacktestResult:
    def __init__(self):
        self.total_trades = 0
        self.wins = 0
        self.losses = 0
        self.total_return = 0.0
        self.max_drawdown = 0.0
        self.sharpe_ratio = 0.0
        self.trades = []

    def to_dict(self) -> dict:
        return {
            "total_trades": self.total_trades,
            "win_rate": round(self.wins / max(self.total_trades, 1), 3),
            "total_return_pct": round(self.total_return * 100, 2),
            "max_drawdown_pct": round(self.max_drawdown * 100, 2),
            "sharpe_ratio": round(self.sharpe_ratio, 2),
            "avg_win": round(np.mean([t["pnl_pct"] for t in self.trades if t["pnl_pct"] > 0] or [0]), 2),
            "avg_loss": round(np.mean([t["pnl_pct"] for t in self.trades if t["pnl_pct"] < 0] or [0]), 2),
            "total_trades_detail": len(self.trades),
        }


def run_backtest(df: pd.DataFrame,
                 signals: list[dict],
                 initial_capital: float = 10000,
                 position_pct: float = 0.2) -> BacktestResult:
    """
    Simple backtest on signal engine output.
    df: OHLCV DataFrame with 'close' column
    signals: [{time, action, score, confidence}] from signal engine
    """
    result = BacktestResult()
    if df.empty:
        return result

    df = df.copy()
    df['date'] = pd.to_datetime(df['time'], unit='ms') if 'time' in df else df.index

    capital = initial_capital
    position = 0
    peak = capital
    daily_returns = []

    for i in range(1, len(df)):
        current_time = df['date'].iloc[i]
        price = float(df['close'].iloc[i])

        # Check for signals at this time
        matching = [s for s in signals
                    if abs(s.get('time', 0) - df['time'].iloc[i]) < 3600000]

        # Trading logic
        if matching and position == 0:
            s = matching[0]
            if s.get('action') in ('STRONG_BUY', 'BUY'):
                position = capital * position_pct / price
                capital -= position * price
                result.total_trades += 1

            elif s.get('action') in ('STRONG_SELL', 'SELL') and position > 0:
                capital += position * price
                pnl = (position * price - position * float(df['close'].iloc[i-1])) /                       (position * float(df['close'].iloc[i-1]))
                result.trades.append({"pnl_pct": round(pnl * 100, 2)})
                if pnl > 0:  result.wins += 1
                else:  result.losses += 1
                position = 0

        # Track equity
        equity = capital + position * price
        peak = max(peak, equity)
        dd = (peak - equity) / peak
        result.max_drawdown = max(result.max_drawdown, dd)

        if i > 1:
            prev_equity = capital + position * float(df['close'].iloc[i-1])
            daily_returns.append((equity - prev_equity) / prev_equity)

    # Close any remaining position
    if position > 0:
        capital += position * float(df['close'].iloc[-1])

    result.total_return = (capital - initial_capital) / initial_capital

    # Sharpe ratio (annualized)
    if daily_returns:
        result.sharpe_ratio = np.mean(daily_returns) / (np.std(daily_returns) + 1e-9) * np.sqrt(365)

    return result
