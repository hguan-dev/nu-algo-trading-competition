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
    """Enhanced trading strategy with dynamic risk management, rate limit management, and additional indicators."""

    def __init__(self) -> None:
        """Initialize the strategy."""
        # Initialize variables
        self.capital: float = 100000.0  # Starting capital
        self.position: Optional[str] = None  # 'long', 'short', or None
        self.position_size: float = 0.0  # Quantity of BTC held
        self.entry_price: Optional[float] = None  # Price at which the position was entered
        self.price_history: List[float] = []  # BTC price history
        self.window_size: int = 20  # Window size for regression
        self.max_position_fraction: float = 0.1  # Max fraction of capital to use per trade
        self.entry_threshold: float = 0.002  # Entry threshold for regression slope
        self.exit_threshold: float = -0.002  # Exit threshold for regression slope
        self.stop_loss_multiplier: float = 1.5  # Multiplier for ATR-based stop-loss
        self.take_profit_multiplier: float = 2.0  # Multiplier for ATR-based take-profit
        self.order_timestamps: List[float] = []  # For rate limiting
        self.max_orders_per_minute: int = 30  # Rate limit
        self.cooldown_period: float = 2.0  # Cooldown period in seconds between orders
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

        if ticker != Ticker.BTC:
            return

        print(f"Python Account update: {ticker.name} {side.name} {price} {quantity} {capital_remaining}")

        # Update capital and position
        self.capital = capital_remaining
        if side == Side.BUY:
            if self.position == 'short':
                self.position_size -= quantity
                if self.position_size <= 0:
                    self.position = None
                    self.entry_price = None
            else:
                self.position_size += quantity
                self.position = 'long'
                self.entry_price = price
        elif side == Side.SELL:
            if self.position == 'long':
                self.position_size -= quantity
                if self.position_size <= 0:
                    self.position = None
                    self.entry_price = None
            else:
                self.position_size += quantity
                self.position = 'short'
                self.entry_price = price

    def execute_trade(self) -> None:
        """Execute trades based on rolling regression slope, RSI, and ATR."""
        if len(self.price_history) < self.window_size:
            return  # Not enough data

        # Calculate regression slope
        prices = self.price_history[-self.window_size:]
        x = np.arange(len(prices)).reshape(-1, 1)
        y = np.array(prices).reshape(-1, 1)
        model = LinearRegression()
        model.fit(x, y)
        slope = model.coef_[0][0] / y.mean()

        # Calculate RSI and ATR
        rsi = self.calculate_rsi(self.price_history)
        atr = self.calculate_atr(self.price_history)
        current_price = prices[-1]

        # Print the regression slope for debugging
        print(f"Regression slope: {slope}, RSI: {rsi}, ATR: {atr}")

        # Stop-loss and take-profit levels
        stop_loss = atr * self.stop_loss_multiplier
        take_profit = atr * self.take_profit_multiplier

        # Check for stop-loss or take-profit
        if self.position and self.entry_price:
            price_change = (current_price - self.entry_price) / self.entry_price
            if self.position == 'long':
                if price_change <= -stop_loss or price_change >= take_profit:
                    # Exit long position
                    quantity = self.position_size
                    if self.place_market_order_with_rate_limit(Side.SELL, Ticker.BTC, quantity):
                        print(f"Exiting long position: Sold {quantity} BTC at {current_price} due to stop-loss/take-profit")
                    return
            elif self.position == 'short':
                if price_change >= stop_loss or price_change <= -take_profit:
                    # Exit short position
                    quantity = abs(self.position_size)
                    if self.place_market_order_with_rate_limit(Side.BUY, Ticker.BTC, quantity):
                        print(f"Exiting short position: Bought {quantity} BTC at {current_price} due to stop-loss/take-profit")
                    return

        # Decide whether to enter or exit position
        if self.position is None:
            if slope > self.entry_threshold and rsi < 70:
                # Upward trend detected; enter long position
                investment = self.capital * self.max_position_fraction
                quantity = investment / current_price
                if self.place_market_order_with_rate_limit(Side.BUY, Ticker.BTC, quantity):
                    print(f"Entering long position: Bought {quantity} BTC at {current_price}")
            elif slope < self.exit_threshold and rsi > 30:
                # Downward trend detected; enter short position
                investment = self.capital * self.max_position_fraction
                quantity = investment / current_price
                if self.place_market_order_with_rate_limit(Side.SELL, Ticker.BTC, quantity):
                    print(f"Entering short position: Sold {quantity} BTC at {current_price}")
        elif self.position == 'long' and slope < self.exit_threshold:
            # Downward trend detected; exit long position
            quantity = self.position_size
            if self.place_market_order_with_rate_limit(Side.SELL, Ticker.BTC, quantity):
                print(f"Exiting long position: Sold {quantity} BTC at {current_price}")
        elif self.position == 'short' and slope > self.entry_threshold:
            # Upward trend detected; exit short position
            quantity = abs(self.position_size)
            if self.place_market_order_with_rate_limit(Side.BUY, Ticker.BTC, quantity):
                print(f"Exiting short position: Bought {quantity} BTC at {current_price}")

    def calculate_rsi(self, prices: List[float], period: int = 14) -> float:
        """Calculate the RSI indicator."""
        if len(prices) < period + 1:
            return 50  # Neutral value when data is insufficient

        deltas = np.diff(prices)
        gains = np.where(deltas > 0, deltas, 0)
        losses = np.where(deltas < 0, -deltas, 0)
        avg_gain = np.mean(gains[-period:])
        avg_loss = np.mean(losses[-period:])

        if avg_loss == 0:
            return 100
        if avg_gain == 0:
            return 0

        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))
        return rsi

    def calculate_atr(self, prices: List[float], period: int = 14) -> float:
        """Calculate the ATR (Average True Range) indicator."""
        if len(prices) < period + 1:
            return 0  # Not enough data for ATR calculation

        tr_list = []
        for i in range(1, len(prices)):
            tr = abs(prices[i] - prices[i - 1])
            tr_list.append(tr)
        atr = np.mean(tr_list[-period:])
        return atr

    def place_market_order_with_rate_limit(self, side: Side, ticker: Ticker, quantity: float) -> bool:
        """Place a market order accounting for the rate limit."""
        current_time = time.time()
        # Remove timestamps older than 60 seconds
        self.order_timestamps = [t for t in self.order_timestamps if current_time - t < 60]

        # Enforce cooldown period
        if self.order_timestamps and (current_time - self.order_timestamps[-1] < self.cooldown_period):
            print("Cooldown period active: Cannot place market order at this time.")
            return False

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
