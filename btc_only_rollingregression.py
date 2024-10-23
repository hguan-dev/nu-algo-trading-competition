from enum import Enum
import time
from collections import defaultdict
from typing import Dict, List, Optional
import numpy as np
from sklearn.linear_model import LinearRegression


class Side(Enum):
    BUY = 0
    SELL = 1


class Ticker(Enum):
    ETH = 0
    BTC = 1
    LTC = 2


def place_market_order(side: Side, ticker: Ticker, quantity: float) -> bool:
    """Place a market order - DO NOT MODIFY"""
    return True


def place_limit_order(side: Side, ticker: Ticker, quantity: float, price: float, ioc: bool = False) -> int:
    """Place a limit order - DO NOT MODIFY"""
    return 0


def cancel_order(ticker: Ticker, order_id: int) -> bool:
    """Cancel a limit order - DO NOT MODIFY"""
    return True


class Strategy:
    """Simplified trading strategy using rolling regression for BTC."""

    def __init__(self) -> None:
        """Initialize the strategy."""
        # Initialize variables
        self.capital: float = 100000.0  # Starting capital
        self.position: Optional[str] = None  # 'long' or None
        self.position_size: float = 0.0  # Quantity of BTC held
        self.price_history: List[float] = []  # BTC price history
        self.window_size: int = 10  # Reduced window size
        self.max_position_fraction: float = 0.5  # Max fraction of capital to use
        self.entry_threshold: float = 0.0  # Lowered entry threshold
        self.exit_threshold: float = -0.001  # Negative exit threshold
        self.order_timestamps: List[float] = []  # For rate limiting
        self.max_orders_per_minute: int = 30  # Rate limit
        self.best_bid: Optional[float] = None
        self.best_ask: Optional[float] = None

    def on_trade_update(self, ticker: Ticker, side: Side, price: float, quantity: float) -> None:
        """Called whenever two orders match."""
        # Only consider BTC
        if ticker != Ticker.BTC:
            return

        print(f"Python Trade update: {ticker.name} {side.name} {price} {quantity}")

        # Update price history
        self.price_history.append(price)
        if len(self.price_history) > self.window_size * 2:
            self.price_history = self.price_history[-self.window_size * 2:]

        # Attempt to execute trades
        self.execute_trade()

    def on_orderbook_update(self, ticker: Ticker, side: Side, price: float, quantity: float) -> None:
        """Update price history based on orderbook updates."""
        # Only consider BTC
        if ticker != Ticker.BTC:
            return

        # Update the best bid and ask prices
        if side == Side.BUY:
            if quantity == 0:
                if self.best_bid == price:
                    self.best_bid = None
            else:
                if self.best_bid is None or price > self.best_bid:
                    self.best_bid = price
        elif side == Side.SELL:
            if quantity == 0:
                if self.best_ask == price:
                    self.best_ask = None
            else:
                if self.best_ask is None or price < self.best_ask:
                    self.best_ask = price

        if self.best_bid is not None and self.best_ask is not None:
            mid_price = (self.best_bid + self.best_ask) / 2
            self.price_history.append(mid_price)
            if len(self.price_history) > self.window_size * 2:
                self.price_history = self.price_history[-self.window_size * 2:]

            # Attempt to execute trades
            self.execute_trade()

    def on_account_update(
        self,
        ticker: Ticker,
        side: Side,
        price: float,
        quantity: float,
        capital_remaining: float,
    ) -> None:
        """Called whenever one of your orders is filled."""
        # Only consider BTC
        if ticker != Ticker.BTC:
            return

        print(f"Python Account update: {ticker.name} {side.name} {price} {quantity} {capital_remaining}")

        # Update capital and position
        self.capital = capital_remaining
        if side == Side.BUY:
            self.position_size += quantity
            self.position = 'long'
        elif side == Side.SELL:
            self.position_size -= quantity
            if self.position_size <= 0:
                self.position = None

    def execute_trade(self) -> None:
        """Execute trades based on rolling regression slope."""
        if len(self.price_history) < self.window_size:
            return  # Not enough data

        # Calculate regression slope
        prices = self.price_history[-self.window_size:]
        x = np.arange(len(prices)).reshape(-1, 1)
        y = np.array(prices).reshape(-1, 1)
        model = LinearRegression()
        model.fit(x, y)
        slope = model.coef_[0][0]

        # Print the regression slope for debugging
        print(f"Regression slope: {slope}")

        # Decide whether to enter or exit position
        current_price = prices[-1]
        position = self.position

        if position is None and slope > self.entry_threshold:
            # Upward trend detected; enter long position
            # Use only a fraction of capital
            investment = self.capital * self.max_position_fraction
            quantity = investment / current_price
            if self.place_market_order_with_rate_limit(Side.BUY, Ticker.BTC, quantity):
                print(f"Entering long position: Bought {quantity} BTC at {current_price}")
        elif position == 'long' and slope < self.exit_threshold:
            # Downward trend detected; exit long position
            quantity = self.position_size
            if self.place_market_order_with_rate_limit(Side.SELL, Ticker.BTC, quantity):
                print(f"Exiting long position: Sold {quantity} BTC at {current_price}")

    def place_market_order_with_rate_limit(self, side: Side, ticker: Ticker, quantity: float) -> bool:
        """Place a market order accounting for the rate limit."""
        current_time = time.time()
        # Remove timestamps older than 60 seconds
        self.order_timestamps = [t for t in self.order_timestamps if current_time - t < 60]

        if len(self.order_timestamps) >= self.max_orders_per_minute:
            print("Rate limit exceeded: Cannot place market order at this time.")
            return False

        success = place_market_order(side, ticker, quantity)
        if success:
            self.order_timestamps.append(current_time)
            print(f"Placed MARKET order: {side.name} {ticker.name} {quantity}")
            return True
        else:
            print(f"Failed to place MARKET order: {side.name} {ticker.name} {quantity}")
            return False