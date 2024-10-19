from enum import Enum
import numpy as np
import pandas as pd
from scipy.stats import zscore

class Side(Enum):
    BUY = 0
    SELL = 1

class Ticker(Enum):
    ETH = 0
    BTC = 1
    LTC = 2

def place_market_order(side: Side, ticker: Ticker, quantity: float) -> bool:
    """Place a market order - DO NOT MODIFY

    Parameters
    ----------
        Side of order to place (Side.BUY or Side.SELL)
    side
    ticker
        Ticker of order to place (Ticker.ETH, Ticker.BTC, or "LTC")
    quantity
        Volume of order to place

    Returns
    -------
    True if order succeeded, False if order failed due to rate limiting

    ((IMPORTANT))
    You should handle the case where the order fails due to rate limiting (maybe wait and try again?)
    """
    return True

def place_limit_order(side: Side, ticker: Ticker, quantity: float, price: float, ioc: bool = False) -> int:
    """Place a limit order - DO NOT MODIFY

    Parameters
    ----------
    side
        Side of order to place (Side.BUY or Side.SELL)
    ticker
        Ticker of order to place (Ticker.ETH, Ticker.BTC, or "LTC")
    quantity
        Volume of order to place
    price
        Price of order to place

    Returns
    -------
    order_id if order succeeded, -1 if order failed due to rate limiting
    """
    return 0

def cancel_order(ticker: Ticker, order_id: int) -> bool:
    """Place a limit order - DO NOT MODIFY
    Parameters
    ----------
    ticker
        Ticker of order to place (Ticker.ETH, Ticker.BTC, or "LTC")
    order_id
        order_id returned by place_limit_order

    Returns
    -------
    True if order succeeded, False if cancellation failed due to rate limiting
    """
    return True

# You can use print() and view the logs after sandbox run has completed
# Might help for debugging
class Strategy:
    """Template for a strategy."""

    def __init__(self, historical_data: pd.DataFrame, threshold: float = 0.02) -> None:
        self.data = historical_data
        self.threshold = threshold
        self.position = None  # Tracks current position ('long' or 'short')
        self.rsi_period = 14
        self.bollinger_period = 20
        self.capital = 100000  # Initial capital
        self.shares = 0       # Shares held

    def calculate_bollinger_bands(self):
        """Calculate Bollinger Bands and add to self.data."""
        self.data['SMA'] = self.data['close'].rolling(self.bollinger_period).mean()
        self.data['stddev'] = self.data['close'].rolling(self.bollinger_period).std()
        self.data['upper_band'] = self.data['SMA'] + 2 * self.data['stddev']
        self.data['lower_band'] = self.data['SMA'] - 2 * self.data['stddev']
        self.data['band_width'] = (self.data['upper_band'] - self.data['lower_band']) / self.data['SMA']

    def calculate_rsi(self):
        """Calculate RSI and add to self.data."""
        delta = self.data['close'].diff(1)
        gain = (delta.where(delta > 0, 0)).rolling(self.rsi_period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(self.rsi_period).mean()
        rs = gain / loss
        self.data['RSI'] = 100 - (100 / (1 + rs))

    def check_bollinger_band_condition(self, row):
        """Check if the price touches or falls below the lower or upper Bollinger Band."""
        if row['close'] <= row['lower_band']:
            return 'long'
        elif row['close'] >= row['upper_band']:
            return 'short'
        return None

    def check_rsi_condition(self, row):
        """Check if RSI is below 25 (oversold) or above 75 (overbought)."""
        if row['RSI'] < 25:
            return 'long'
        elif row['RSI'] > 75:
            return 'short'
        return None

    def execute_trade(self, row, ticker: Ticker):
        """Execute trade based on strategy conditions."""
        if self.position == 'long':
            # Exit long position if price rises to the SMA or RSI is above 50
            if row['close'] >= row['SMA'] or row['RSI'] > 50:
                print(f"Exiting long position at {row['close']}")
                self.capital += self.shares * row['close']
                self.shares = 0
                self.position = None
        elif self.position == 'short':
            # Exit short position if price falls to the SMA or RSI is below 50
            if row['close'] <= row['SMA'] or row['RSI'] < 50:
                print(f"Exiting short position at {row['close']}")
                self.capital += self.shares * (2 * row['SMA'] - row['close'])  # Cover short
                self.shares = 0
                self.position = None
        else:
            if row['band_width'] > self.threshold:
                bollinger_signal = self.check_bollinger_band_condition(row)
                rsi_signal = self.check_rsi_condition(row)

                if bollinger_signal == 'long' and rsi_signal == 'long':
                    # Enter long position
                    self.position = 'long'
                    self.shares = self.capital / row['close']
                    self.capital = 0
                    print(f"Entering long position at {row['close']}")
                elif bollinger_signal == 'short' and rsi_signal == 'short':
                    # Enter short position
                    self.position = 'short'
                    self.shares = self.capital / row['close']
                    self.capital = 0
                    print(f"Entering short position at {row['close']}")

    def run(self, ticker: Ticker):
        """Main function to run the strategy over historical data."""
        self.calculate_bollinger_bands()
        self.calculate_rsi()

        for _, row in self.data.iterrows():
            self.execute_trade(row, ticker)

        print(f"Final capital: {self.capital}")

    def on_trade_update(self, ticker: Ticker, side: Side, quantity: float, price: float) -> None:
        """Called whenever two orders match. Could be one of your orders, or two other people's orders.

        Parameters
        ----------
        ticker
            Ticker of orders that were matched (Ticker.ETH, Ticker.BTC, or "LTC")
        side 
            Side of orders that were matched (Side.BUY or Side.SELL)
        price
            Price that trade was executed at
        quantity
            Volume traded
        """
        print(f"Python Trade update: {ticker} {side} {price} {quantity}")

    def on_orderbook_update(
        self, ticker: Ticker, side: Side, quantity: float, price: float
    ) -> None:
        """Called whenever the orderbook changes. This could be because of a trade, or because of a new order, or both.

        Parameters
        ----------
        ticker
            Ticker that has an orderbook update (Ticker.ETH, Ticker.BTC, or "LTC")
        side
            Which orderbook was updated (Side.BUY or Side.SELL)
        price
            Price of orderbook that has an update
        quantity
            Volume placed into orderbook
        """
        print(f"Python Orderbook update: {ticker} {side} {price} {quantity}")

    def on_account_update(
        self,
        ticker: Ticker,
        side: Side,
        price: float,
        quantity: float,
        capital_remaining: float,
    ) -> None:
        """Called whenever one of your orders is filled.

        Parameters
        ----------
        ticker
            Ticker of order that was fulfilled (Ticker.ETH, Ticker.BTC, or "LTC")
        side
            Side of order that was fulfilled (Side.BUY or Side.SELL)
        price
            Price that order was fulfilled at
        quantity
            Volume of order that was fulfilled
        capital_remaining
            Amount of capital after fulfilling order
        """
        self.capital = capital_remaining
        print(
            f"Python Account update: {ticker} {side} {price} {quantity} {capital_remaining}"
        )
