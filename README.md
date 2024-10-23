This repo is used to compete in Northwestern University Trading Competition 2024.

We are given the template files to implemnet trading strategy using functions:
```on_orderbook_update```, ```on_trade_update```, and ```on_account_update```

Our strategy is high-frequency trading mean-reversions strategy for Bitcoin (BTC), Ethereum (ETH), and Litecoin (LTC), with a focus on price volatility and volume. We ensure that no position grows larger than the allocated capital for each asset

**Note:** Transaction fee of 0.004 or 40 basis points is applied in exchange.

## Capital and Allocation
The algorithm starts with a capital of 100,000 units (e.g., USD). It maintains an allocation of 50% for BTC and divides the remaining 50% equally between ETH and LTC.


## Trading Logic
The strategy makes trading decisions based on the current price relative to VWAP and volatility:

**Buy Signals:** If the price drops below VWAP minus volatility, the algorithm places a buy limit order for the asset if enough capital is available, aiming to buy at a slightly lower price (0.999 times the current price).

**Sell Signals:** If the price rises above VWAP plus volatility and the algorithm holds the asset, it places a sell limit order, aiming to sell at a slightly higher price (1.001 times the current price).

