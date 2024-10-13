from enum import Enum
import time
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
    """Place a market order - DO NOT MODIFY
    ...
    """
    return True

def place_limit_order(side: Side, ticker: Ticker, quantity: float, price: float, ioc: bool = False) -> int:
    """Place a limit order - DO NOT MODIFY
    ...
    """
    return 0

def cancel_order(ticker: Ticker, order_id: int) -> bool:
    """Cancel an order - DO NOT MODIFY
    ...
    """
    return True

class Strategy:
    """Trading strategy using a regression model to find price discrepancies."""

    def __init__(self) -> None:
        """Initialize data structures and regression models."""
        # Price and time history for each ticker
        self.price_history = {ticker: [] for ticker in Ticker}
        self.time_history = {ticker: [] for ticker in Ticker}
        # Regression models for each ticker
        self.models = {ticker: LinearRegression() for ticker in Ticker}
        # Last update time
        self.last_time = time.time()
        # Parameters
        self.N = 50  # Number of data points to keep
        self.threshold = 0.001  # 0.1% price discrepancy threshold

    def on_orderbook_update(
        self, ticker: Ticker, side: Side, quantity: float, price: float
    ) -> None:
        """Called whenever the orderbook changes."""
        current_time = time.time()
        elapsed_time = current_time - self.last_time
        self.last_time = current_time

        # Store the price and timestamp
        self.price_history[ticker].append(price)
        self.time_history[ticker].append(current_time)

        # Keep only the last N data points
        if len(self.price_history[ticker]) > self.N:
            self.price_history[ticker] = self.price_history[ticker][-self.N :]
            self.time_history[ticker] = self.time_history[ticker][-self.N :]

        # If we have enough data points, update the model
        if len(self.price_history[ticker]) >= 10:
            times = np.array(self.time_history[ticker]).reshape(-1, 1)
            prices = np.array(self.price_history[ticker])
            # Fit the regression model
            self.models[ticker].fit(times, prices)

            # Predict the price 1 second into the future
            future_time = np.array([[current_time + 1]])
            predicted_price = self.models[ticker].predict(future_time)[0]

            # Calculate the percentage difference
            price_diff = (predicted_price - price) / price

            # Decide whether to place a buy or sell order
            if price_diff > self.threshold:
                # Predicted price is significantly higher; place a buy order
                self.place_order_with_retry(Side.BUY, ticker, quantity=0.01)
            elif price_diff < -self.threshold:
                # Predicted price is significantly lower; place a sell order
                self.place_order_with_retry(Side.SELL, ticker, quantity=0.01)

    def place_order_with_retry(self, side: Side, ticker: Ticker, quantity: float):
        """Attempt to place an order, handling rate limiting."""
        max_retries = 5
        retry_delay = 0.1  # seconds
        for attempt in range(max_retries):
            success = place_market_order(side, ticker, quantity)
            if success:
                print(f"Placed {side.name} order for {quantity} {ticker.name}")
                return
            else:
                print(f"Order failed due to rate limiting. Retrying in {retry_delay} seconds...")
                time.sleep(retry_delay)
        print(f"Failed to place {side.name} order for {ticker.name} after {max_retries} attempts.")

    def on_trade_update(self, ticker: Ticker, side: Side, quantity: float, price: float) -> None:
        """Called whenever two orders match."""
        print(f"Trade update: {ticker.name} {side.name} {quantity} @ {price}")

    def on_account_update(
        self,
        ticker: Ticker,
        side: Side,
        price: float,
        quantity: float,
        capital_remaining: float,
    ) -> None:
        """Called whenever one of your orders is filled."""
        print(
            f"Account update: {ticker.name} {side.name} {quantity} @ {price}, Capital Remaining: {capital_remaining}"
        )
