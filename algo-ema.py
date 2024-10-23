from enum import Enum
from collections import defaultdict
from typing import List, Dict
import numpy as np

class Side(Enum):
    BUY = 0
    SELL = 1

class Ticker(Enum):
    ETH = 0
    BTC = 1
    LTC = 2

def place_market_order(side: Side, ticker: Ticker, quantity: float) -> bool:
    return True

def place_limit_order(side: Side, ticker: Ticker, quantity: float, price: float, ioc: bool = False) -> int:
    return 0

def cancel_order(ticker: Ticker, order_id: int) -> bool:
    return True

class Strategy:
    def __init__(self):
        self.capital = 100000.0
        self.holdings: Dict[Ticker, float] = {Ticker.BTC: 0.0, Ticker.ETH: 0.0, Ticker.LTC: 0.0}
        self.prices: Dict[Ticker, List[float]] = defaultdict(list)
        self.volumes: Dict[Ticker, List[float]] = defaultdict(list)
        self.open_orders: Dict[Ticker, Dict[int, float]] = defaultdict(dict)
        self.fee_rate = 0.004  # 40 bps fee
        self.window_size = 50
        self.btc_allocation = 0.5

    def on_trade_update(self, ticker: Ticker, side: Side, quantity: float, price: float) -> None:
        self.prices[ticker].append(price)
        self.volumes[ticker].append(quantity)
        if len(self.prices[ticker]) > self.window_size:
            self.prices[ticker].pop(0)
            self.volumes[ticker].pop(0)

    def on_orderbook_update(self, ticker: Ticker, side: Side, quantity: float, price: float) -> None:
        if len(self.prices[ticker]) < self.window_size:
            return

        vwap = np.average(self.prices[ticker], weights=self.volumes[ticker])
        volatility = np.std(self.prices[ticker])

        if ticker == Ticker.BTC:
            allocation = self.btc_allocation
        else:
            allocation = (1 - self.btc_allocation) / 2

        available_capital = self.capital * allocation
        position_value = self.holdings[ticker] * price

        if price < vwap - volatility and position_value < available_capital:
            quantity = min((available_capital - position_value) / price, 1.0)
            order_id = place_limit_order(Side.BUY, ticker, quantity, price * 0.999)
            self.open_orders[ticker][order_id] = quantity
        elif price > vwap + volatility and self.holdings[ticker] > 0:
            quantity = min(self.holdings[ticker], 1.0)
            order_id = place_limit_order(Side.SELL, ticker, quantity, price * 1.001)
            self.open_orders[ticker][order_id] = quantity

        # Cancel old orders
        for order_id in list(self.open_orders[ticker].keys()):
            if cancel_order(ticker, order_id):
                del self.open_orders[ticker][order_id]

    def on_account_update(self, ticker: Ticker, side: Side, price: float, quantity: float, capital_remaining: float) -> None:
        fee = price * quantity * self.fee_rate
        if side == Side.BUY:
            self.holdings[ticker] += quantity
            self.capital -= price * quantity + fee
        else:
            self.holdings[ticker] -= quantity
            self.capital += price * quantity - fee

        self.capital = capital_remaining

    def calculate_vwap(self, ticker: Ticker) -> float:
        return np.average(self.prices[ticker], weights=self.volumes[ticker])

    def calculate_volatility(self, ticker: Ticker) -> float:
        return np.std(self.prices[ticker])
    