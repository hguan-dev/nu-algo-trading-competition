from enum import Enum
import time
from collections import defaultdict
from typing import Dict, List, Optional
import numpy as np
import pandas as pd

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
    def __init__(self) -> None:
        self.order_ids: Dict[int, Dict] = {}
        self.prices: Dict[Ticker, float] = {}
        self.capital: float = 100000.0
        self.positions: Dict[Ticker, List[Dict]] = defaultdict(list)
        self.price_history: Dict[Ticker, List[float]] = defaultdict(list)
        self.rsi_history: Dict[Ticker, List[float]] = defaultdict(list)
        self.order_book: Dict[Ticker, Dict[str, Dict[float, float]]] = defaultdict(
            lambda: {'buy': defaultdict(float), 'sell': defaultdict(float)}
        )
        self.rsi_window: int = 21
        self.bb_window: int = 30
        self.bb_std_dev: float = 2.0
        self.minimum_band_width: float = 0.01
        self.max_position_size_percentage: float = 0.05  # Maximum 5% of capital per position

    def on_trade_update(self, ticker: Ticker, side: Side, quantity: float, price: float) -> None:
        self.price_history[ticker].append(price)
        if len(self.price_history[ticker]) > self.bb_window:
            self.price_history[ticker].pop(0)

        self.prices[ticker] = price
        self.execute_mean_reversion_on_orderbook(ticker)
        self.check_divergence(ticker)

    def on_orderbook_update(
        self, ticker: Ticker, side: Side, quantity: float, price: float
    ) -> None:
        """Called whenever the orderbook changes. This could be because of a trade, or because of a new order, or both."""
        print(f"Orderbook update: {ticker.name} {side.name} {price} {quantity}")

        if quantity == 0:
            if price in self.order_book[ticker][side.name.lower()]:
                del self.order_book[ticker][side.name.lower()][price]
                print(f"Removed {side.name} order at {price} for {ticker.name} from local order book.")
        else:
            self.order_book[ticker][side.name.lower()][price] = quantity
            print(f"Updated {side.name} order at {price} for {ticker.name} with quantity {quantity} in local order book.")

        self.execute_mean_reversion_on_orderbook(ticker)
        self.check_divergence(ticker)

    def execute_mean_reversion_on_orderbook(self, ticker: Ticker) -> None:
        """Executes the mean reversion strategy based on the latest order book update."""
        if len(self.price_history[ticker]) < self.bb_window:
            return

        prices = np.array(self.price_history[ticker])
        sma = np.mean(prices)
        std_dev = np.std(prices)

        upper_band = sma + self.bb_std_dev * std_dev
        lower_band = sma - self.bb_std_dev * std_dev
        current_price = self.prices[ticker]

        band_width = (upper_band - lower_band) / sma
        if band_width < self.minimum_band_width:
            return

        rsi = self.calculate_rsi(prices)
        self.rsi_history[ticker].append(rsi)

        position_size = self.calculate_position_size(current_price)

        # Long position criteria
        if current_price <= lower_band and rsi < 30:
            order_id = self.place_limit_order(Side.BUY, ticker, position_size, current_price, ioc=True)
            if order_id:
                self.positions[ticker].append({'order_id': order_id, 'side': Side.BUY, 'price': current_price, 'quantity': position_size})
                print(f"Orderbook Mean Reversion: Placed BUY order for {ticker.name} at {current_price} with order ID {order_id}")

        # Short position criteria
        elif current_price >= upper_band and rsi > 75:
            order_id = self.place_limit_order(Side.SELL, ticker, position_size, current_price, ioc=True)
            if order_id:
                self.positions[ticker].append({'order_id': order_id, 'side': Side.SELL, 'price': current_price, 'quantity': position_size})
                print(f"Orderbook Mean Reversion: Placed SELL order for {ticker.name} at {current_price} with order ID {order_id}")

    def on_account_update(self, ticker: Ticker, side: Side, price: float, quantity: float, capital_remaining: float) -> None:
        self.capital = capital_remaining
        if side == Side.BUY:
            self.positions[ticker].append({'price': price, 'quantity': quantity, 'side': side})
        elif side == Side.SELL:
            self.positions[ticker].append({'price': price, 'quantity': quantity, 'side': side})

    def check_divergence(self, ticker: Ticker) -> None:
        """Checks for divergence based on RSI and price movement patterns."""
        if len(self.price_history[ticker]) < self.bb_window or len(self.rsi_history[ticker]) < 2:
            return

        prices = np.array(self.price_history[ticker])
        rsi_values = np.array(self.rsi_history[ticker])
        current_price = self.prices[ticker]

        # Bullish Divergence
        if len(prices) >= 2 and len(rsi_values) >= 2:
            price_low = prices[-2]
            price_current = prices[-1]
            rsi_low = rsi_values[-2]
            rsi_current = rsi_values[-1]

            if price_current < price_low and rsi_current > rsi_low:
                position_size = self.calculate_position_size(current_price)
                order_id = self.place_limit_order(Side.BUY, ticker, position_size, current_price, ioc=True)
                if order_id:
                    self.positions[ticker].append({'order_id': order_id, 'side': Side.BUY, 'price': current_price, 'quantity': position_size})
                    print(f"Divergence: Bullish - Placed BUY order for {ticker.name} at {current_price} with order ID {order_id}")

        # Bearish Divergence
        if len(prices) >= 2 and len(rsi_values) >= 2:
            price_high = prices[-2]
            price_current = prices[-1]
            rsi_high = rsi_values[-2]
            rsi_current = rsi_values[-1]

            if price_current > price_high and rsi_current < rsi_high:
                position_size = self.calculate_position_size(current_price)
                order_id = self.place_limit_order(Side.SELL, ticker, position_size, current_price, ioc=True)
                if order_id:
                    self.positions[ticker].append({'order_id': order_id, 'side': Side.SELL, 'price': current_price, 'quantity': position_size})
                    print(f"Divergence: Bearish - Placed SELL order for {ticker.name} at {current_price} with order ID {order_id}")

    def calculate_rsi(self, prices: np.ndarray) -> float:
        if len(prices) < self.rsi_window:
            return 50  # Neutral if not enough data
        
        delta = np.diff(prices)
        gain = np.where(delta > 0, delta, 0)
        loss = np.where(delta < 0, -delta, 0)

        avg_gain = np.mean(gain[-self.rsi_window:])
        avg_loss = np.mean(loss[-self.rsi_window:])
        
        if avg_loss == 0:
            return 100  # RSI maxes out if no loss

        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))
        return rsi

    def calculate_position_size(self, price: float) -> float:
        """Calculates position size based on available capital and price."""
        max_position_size = self.capital * self.max_position_size_percentage
        position_size = max_position_size / price
        return position_size

    def place_limit_order(self, side: Side, ticker: Ticker, quantity: float, price: float, ioc: bool = False) -> Optional[int]:
        try:
            order_id = place_limit_order(side, ticker, quantity, price, ioc)
            if order_id != 0:
                self.order_ids[order_id] = {'ticker': ticker, 'side': side, 'ioc': ioc}
                print(f"Placed LIMIT order: {side.name} {ticker.name} {quantity} @ {price} with order ID {order_id}")
                return order_id
            else:
                print(f"Failed to place LIMIT order: {side.name} {ticker.name} {quantity} @ {price}")
                return None
        except Exception as e:
            print(f"Error placing LIMIT order: {e}")
            return None
