#!/usr/bin/env python3
"""
Execution Engine — Layer 5/6
Simulated trading execution (Phase 4: paper trading)
"""

import logging
from datetime import datetime
from typing import Optional

logger = logging.getLogger(__name__)


class Order:
    def __init__(self, symbol: str, side: str, order_type: str,
                 price: float, quantity: float):
        self.symbol = symbol
        self.side = side  # BUY / SELL
        self.type = order_type  # MARKET / LIMIT
        self.price = price
        self.quantity = quantity
        self.status = "PENDING"
        self.filled_price = 0
        self.filled_quantity = 0
        self.created_at = datetime.now()
        self.filled_at = None


class ExecutionEngine:
    """Simulated execution engine for paper trading"""

    def __init__(self, slippage_pct: float = 0.001):
        self.slippage_pct = slippage_pct
        self.orders = []
        self.positions = {}  # symbol -> {shares, avg_price}

    def create_order(self, symbol: str, side: str, price: float,
                     quantity: float, order_type: str = "LIMIT") -> Order:
        """Create a new order"""
        order = Order(symbol, side, order_type, price, quantity)
        self.orders.append(order)
        return order

    def execute_market(self, symbol: str, side: str,
                       price: float, quantity: float) -> Order:
        """Execute a market order with simulated slippage"""
        slip = price * self.slippage_pct
        filled_price = price + slip if side == "BUY" else price - slip

        order = self.create_order(symbol, side, "MARKET", price, quantity)
        order.status = "FILLED"
        order.filled_price = round(filled_price, 2)
        order.filled_quantity = quantity
        order.filled_at = datetime.now()

        self._update_position(symbol, side, order.filled_price, quantity)
        logger.info(f"EXECUTED {side} {quantity} {symbol} @ {order.filled_price}")
        return order

    def cancel_order(self, order: Order):
        """Cancel a pending order"""
        order.status = "CANCELLED"

    def get_position(self, symbol: str) -> Optional[dict]:
        """Get current position for a symbol"""
        return self.positions.get(symbol)

    def get_all_positions(self) -> list[dict]:
        """Get all open positions"""
        return [{"symbol": s, **p} for s, p in self.positions.items()
                if p["shares"] > 0]

    def close_all(self, current_prices: dict[str, float]):
        """Close all positions at current prices"""
        for symbol, pos in list(self.positions.items()):
            if pos["shares"] > 0:
                price = current_prices.get(symbol, pos["avg_price"])
                side = "SELL" if pos["shares"] > 0 else "BUY"
                self.execute_market(symbol, side, price, abs(pos["shares"]))
        logger.info("All positions closed")

    def _update_position(self, symbol: str, side: str,
                         price: float, quantity: float):
        """Update position after fill"""
        if symbol not in self.positions:
            self.positions[symbol] = {"shares": 0, "avg_price": 0}

        pos = self.positions[symbol]
        if side == "BUY":
            total_cost = pos["avg_price"] * pos["shares"] + price * quantity
            pos["shares"] += quantity
            pos["avg_price"] = total_cost / pos["shares"] if pos["shares"] > 0 else 0
        else:  # SELL
            pos["shares"] -= quantity
            if pos["shares"] <= 0:
                self.positions[symbol] = {"shares": 0, "avg_price": 0}
