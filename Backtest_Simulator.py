from datetime import datetime, timedelta
from termcolor import colored
from tqdm import tqdm

import plotly.graph_objects as go
import streamlit as st
import sqlite3 as db
import pandas as pd
import yfinance as yf
import numpy as np

# import pandas_ta
import ccxt
import ta


def fetch_data(symbol, timeframe, interval, since):
    exchange = ccxt.binance()
    all_ohlcv = []
    fetch_limit = 500

    # Connecting to the database
    connection = db.connect("market_data.db")
    cursor = connection.cursor()

    # Fetching all of the table names and checking for existence
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    table_names = [name[0] for name in cursor.fetchall()]
    table_name = symbol.replace("/", "_") + "_" + timeframe
    # TODO: Comment this out if you want to pull new data
    # if table_name in table_names:
    #     data = pd.read_sql_query(
    #         "SELECT * FROM " + table_name, connection
    #     ).set_index("index")
    #     data["timestamp"] = pd.to_datetime(
    #         data["timestamp"], format="%Y-%m-%d %H:%M:%S"
    #     )
    #     return data

    # Calculate the number of iterations needed
    now = datetime.now()
    since_datetime = datetime.fromtimestamp(since / 1000)
    total_minutes = (now - since_datetime).total_seconds() / 60
    num_intervals = total_minutes / interval
    num_iterations = int(num_intervals / fetch_limit) + 1

    for _ in tqdm(range(num_iterations), desc="fetch_data", leave=False):
        ohlcv = exchange.fetch_ohlcv(symbol, timeframe, since=since)
        if not ohlcv:
            break
        all_ohlcv.extend(ohlcv)
        # Move to the next timestamp to avoid duplicate data
        since = ohlcv[-1][0] + 1
        if len(ohlcv) < fetch_limit:
            break  # Break the loop if less than 500 rows are returned

    data = pd.DataFrame(
        all_ohlcv,
        columns=["timestamp", "open", "high", "low", "close", "volume"],
    )
    data["timestamp"] = pd.to_datetime(data["timestamp"], unit="ms")
    # data.to_sql(table_name, connection)
    connection.commit()
    cursor.close()
    connection.close()
    return data


def calculate_rsi(data, period=14):
    data["rsi"] = ta.momentum.RSIIndicator(data["close"], window=period).rsi()
    return data


def calculate_stochastic_rsi(data, period=14):
    data["stochastic_rsi"] = (
        ta.momentum.StochRSIIndicator(data["close"], window=period).stochrsi()
        * 100
    )
    return data


def calculate_price_oscillator(data):
    data["price_oscillator"] = ta.momentum.PercentagePriceOscillator(
        data["close"]
    ).ppo()
    return data


def calculate_ema(data, period=14):
    data["ema"] = ta.trend.EMAIndicator(
        data["close"], window=period
    ).ema_indicator()
    return data


def calculate_double_ema(data, period=14):
    EMA = ta.trend.EMAIndicator(data["close"], window=period).ema_indicator()
    data["double_ema"] = (
        2 * EMA - ta.trend.EMAIndicator(EMA, window=period).ema_indicator()
    )
    return data


def calculate_supertrend(data):
    # data["supertrend_len12_mult3"] = pandas_ta.supertrend(
    #     data["high"], data["low"], data["close"], length=12, multiplier=3
    # )["SUPERTd_12_3.0"]
    # data["supertrend_len11_mult2"] = pandas_ta.supertrend(
    #     data["high"], data["low"], data["close"], length=11, multiplier=2
    # )["SUPERTd_11_2.0"]
    # data["supertrend_len10_mult1"] = pandas_ta.supertrend(
    #     data["high"], data["low"], data["close"], length=10, multiplier=1
    # )["SUPERTd_10_1.0"]
    return data


# Function to get the spot price from YFinance
def get_spot_price(symbol):
    end_date = datetime.now()
    start_date = end_date - timedelta(days=20)

    # Pulling minute-level data
    data = yf.download(
        symbol,
        start=start_date.strftime("%Y-%m-%d"),
        end=end_date.strftime("%Y-%m-%d"),
        interval="5m",
        progress=False,
    )

    # Format the data
    coin_data = (
        data["Close"]
        .reset_index()
        .rename(
            columns={"Datetime": "timestamp", "Close": "price"}
        )  # Adjust column names
    )
    return coin_data


# Function to get the perpetual futures price from YFinance
def get_perpetual_price(symbol):
    end_date = datetime.now()
    start_date = end_date - timedelta(days=20)

    data = yf.download(
        symbol,
        start=start_date.strftime("%Y-%m-%d"),
        end=end_date.strftime("%Y-%m-%d"),
        interval="5m",
        progress=False,
    )
    coin_data = (
        data["Close"]
        .reset_index()
        .rename(columns={"Datetime": "timestamp", "Close": "price"})
    )
    coin_data["timestamp"] = coin_data["timestamp"].dt.tz_convert("UTC")
    return coin_data


# Function to calculate the basis
def calculate_basis(spot_symbol, perpetual_symbol):
    spot_price = get_spot_price(spot_symbol)
    perpetual_price = get_perpetual_price(perpetual_symbol)
    merged_data = pd.merge_asof(
        perpetual_price.sort_values("timestamp"),
        spot_price.sort_values("timestamp"),
        on="timestamp",
        direction="backward",
        suffixes=("_perpetual", "_spot"),
    )
    merged_data["basis"] = (
        (merged_data["price_perpetual"] - merged_data["price_spot"])
        / merged_data["price_spot"]
    ) * 100
    return merged_data


def backtest(data, initial_balance, fee, strategy):
    final_balance = 0
    percentage_return = 0
    previous_balance = initial_balance  # keeping track of the previous balance
    balance = initial_balance
    bitcoin_balance = 0
    position = None
    gain_count = 0  # number of gains
    loss_count = 0  # number of losses
    total_fees = 0
    start_dates = []  # list of all entry point dates
    end_dates = []  # list of all exit point dates
    balance_deltas = []

    for i in tqdm(range(1, len(data)), desc="backtest", leave=False):
        if previous_balance <= 0:
            return (
                final_balance,
                percentage_return,
                gain_count,
                loss_count,
                total_fees,
                (start_dates, end_dates),
                balance_deltas,
            )
        updated_balance = bitcoin_balance * data["close"].iloc[i]
        percent_change = (updated_balance - previous_balance) / previous_balance
        if (
            data["rsi"].iloc[i] <= strategy["rsi_entry"]
            # data["stochastic_rsi"].iloc[i] <= strategy["stochastic_rsi_entry"]
            and data["price_oscillator"].iloc[i]
            <= strategy["price_oscillator_entry"]
            # and data["supertrend_len12_mult3"].iloc[i] == 1
            # data["supertrend_len11_mult2"].iloc[i] == 1
            # and data["supertrend_len10_mult1"].iloc[i] == 1
            # data["double_ema"].iloc[i] < data["close"].iloc[i]
            and position is None
        ):
            total_fees += balance * fee
            balance *= 1 - fee
            bitcoin_balance = balance / data["close"].iloc[i]
            previous_balance = balance
            balance = 0
            position = "long"
            start_dates.append(data["timestamp"].iloc[i])

        elif (
            (
                False
                # data["rsi"].iloc[i] >= strategy["rsi_exit"]
                # data["stochastic_rsi"].iloc[i] >= strategy["stochastic_rsi_exit"]
                # and data["price_oscillator"].iloc[i] >= strategy["price_oscillator_exit"]
                # data["supertrend_len12_mult3"].iloc[i] == -1
                # data["supertrend_len11_mult2"].iloc[i] == -1
                # data["supertrend_len10_mult1"].iloc[i] == -1
                and position == "long"
            )
            or percent_change >= strategy["take_profit"]
            # or percent_change <= strategy["stop_loss"]
        ):
            total_fees += updated_balance * fee
            updated_balance *= 1 - fee
            if updated_balance > previous_balance:
                gain_count += 1
            else:
                loss_count += 1
            balance_deltas.append(percent_change)
            balance = updated_balance
            bitcoin_balance = 0
            position = None
            end_dates.append(data["timestamp"].iloc[i])

    final_balance = balance + (bitcoin_balance * data["close"].iloc[-1])
    percentage_return = (
        (final_balance - initial_balance) / initial_balance * 100
    )

    return (
        final_balance,
        percentage_return,
        gain_count,
        loss_count,
        total_fees,
        (start_dates, end_dates),
        balance_deltas,
    )


if __name__ == "__main__":
    st.set_page_config(layout="wide")
    st.title("Backtest Simulator")

    col1, col2, col3 = st.columns(3)
    with col1:
        initial_balance = st.number_input(
            "Initial Balance",
            min_value=0,
            max_value=1000000,
            value=10000,
            step=1000,
        )
        rsi_entry = st.number_input(
            "RSI Entry", min_value=0, max_value=100, value=30, step=1
        )
        # stochastic_rsi_entry = st.number_input(
        #     "Stochastic RSI Entry", min_value=0, max_value=100, value=20, step=1
        # )
        price_oscillator_entry = st.number_input(
            "Price Oscillator Entry",
            min_value=-5.0,
            max_value=5.0,
            value=-0.45,
            step=0.05,
            format="%.2f",
        )
    with col2:
        timeframe = st.selectbox(
            "Timeframe", ["5m", "15m", "1h", "1d"], index=1
        )
        rsi_exit = st.number_input(
            "RSI Exit", min_value=0, max_value=100, value=70, step=1
        )
        # stochastic_rsi_exit = st.number_input(
        #     "Stochastic RSI Exit", min_value=0, max_value=100, value=80, step=1
        # )
        price_oscillator_exit = st.number_input(
            "Price Oscillator Exit",
            min_value=-5.0,
            max_value=5.0,
            value=0.5,
            step=0.05,
            format="%.2f",
        )
    with col3:
        lookback = st.number_input(
            "Lookback Period",
            min_value=0,
            max_value=365 * 3,
            value=365,
            step=1,
        )
        take_profit = st.number_input(
            "Take Profit",
            min_value=0.0,
            max_value=1.0,
            value=0.015,
            step=0.001,
            format="%.3f",
        )
        stop_loss = st.number_input(
            "Stop Loss",
            min_value=-1.0,
            max_value=0.0,
            value=-0.005,
            step=0.001,
            format="%.3f",
        )

    symbols = ["BTC/USDT", "ETH/USDT", "SOL/USDT", "DOGE/USDT", "LTC/USDT"]
    intervals = {"5m": 5, "15m": 15, "1h": 60, "1d": 1440}
    interval = intervals[timeframe]  # the time interval in numerical format
    since = int((datetime.now() - timedelta(days=lookback)).timestamp() * 1000)
    fee = 0.001

    # BUILD A STRATEGY
    strategy = {
        "rsi_entry": rsi_entry,
        "rsi_exit": rsi_exit,
        # "stochastic_rsi_entry": stochastic_rsi_entry,
        # "stochastic_rsi_exit": stochastic_rsi_exit,
        "price_oscillator_entry": price_oscillator_entry,
        "price_oscillator_exit": price_oscillator_exit,
        "take_profit": take_profit,
        "stop_loss": stop_loss,
    }

    launch_backtesting = st.button("Launch Backtesting")

    if launch_backtesting:
        for symbol in symbols:
            data = fetch_data(symbol, timeframe, interval, since)
            data = calculate_rsi(data)
            data = calculate_stochastic_rsi(data)
            data = calculate_price_oscillator(data)
            data = calculate_supertrend(data)
            data = calculate_ema(data)
            data = calculate_double_ema(data, 200)

            spot_symbol = "BTC-USD"
            perpetual_symbol = "BTC=F"
            basis = calculate_basis(spot_symbol, perpetual_symbol)

            start_time = pd.Timestamp.now(tz="UTC") - datetime.timedelta(
                hours=23
            )
            basis_interval = basis[(basis["timestamp"] >= start_time)]

            x_timestamps = np.array(
                (
                    basis_interval["timestamp"]
                    - basis_interval["timestamp"].min()
                ).dt.total_seconds()
            )
            y_basis = basis_interval["basis"].values

            coefficients_basis = np.polyfit(x_timestamps, y_basis, 1)
            regression_line_basis = np.polyval(coefficients_basis, x_timestamps)

            (
                final_balance,
                percentage_return,
                gain_count,
                loss_count,
                total_fees,
                (start_dates, end_dates),
                balance_deltas,
            ) = backtest(data, initial_balance, fee, strategy)

            print(colored(symbol, "cyan"))
            st.markdown(
                f"<span style='color:cyan;'>{symbol}</span>",
                unsafe_allow_html=True,
            )
            if len(end_dates) == 0:
                print(colored("NO TRADES WERE MADE", "yellow"))
                st.markdown(
                    f"<span style='color:yellow;'>NO TRADES WERE MADE</span>",
                    unsafe_allow_html=True,
                )
                continue

            deltas = [
                end_date - start_date
                for start_date, end_date in zip(start_dates, end_dates)
            ]
            print(
                colored("Init. Bal.: ", "blue")
                + f"{initial_balance}  "
                + colored("Final Bal.: ", "blue")
                + f"{final_balance:.2f}  "
                + colored("Avg. Holding Period: ", "blue")
                + f"{(sum(deltas, timedelta()) / len(deltas))}"
            )
            success_rate = gain_count / (gain_count + loss_count) * 100
            print(
                colored("Return: ", "magenta")
                + f"{percentage_return:.2f}%  "
                + colored("Avg. Return: ", "magenta")
                + f"{sum(balance_deltas) / len(balance_deltas) * 100:.2f}%  "
                + colored("Success Rate: ", "magenta")
                + f"{success_rate:.2f}%"
            )
            print(
                colored("Gains: ", "green")
                + f"{gain_count}  "
                + colored("Losses: ", "red")
                + f"{loss_count}  "
                + colored("Total Fees: ", "red")
                + f"{total_fees:.2f}  "
                + colored("Total: ", "blue")
                + f"{gain_count + loss_count}"
            )

            # Displaying the key statistics in Streamlit
            # TODO: Add more key statistics
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.markdown(
                    f"<span style='color:blue;'>**Initial Balance:**</span> \
                    <span style='font-weight:bold;'>{initial_balance}</span>",
                    unsafe_allow_html=True,
                )
            with col2:
                st.markdown(
                    f"<span style='color:magenta;'>**Final Balance:**</span> \
                    <span style='font-weight:bold;'>{final_balance}</span>",
                    unsafe_allow_html=True,
                )
            with col3:
                st.markdown(
                    f"<span style='color:magenta;'>**Percentage Return:**</span> \
                    <span style='font-weight:bold;'>{percentage_return}%</span>",
                    unsafe_allow_html=True,
                )
            with col4:
                st.markdown(
                    f"<span style='color:green;'>**Gains:**</span> \
                    <span style='font-weight:bold;'>{gain_count}</span> &nbsp; &nbsp; &nbsp;"
                    f"<span style='color:red;'>**Losses:**</span> \
                    <span style='font-weight:bold;'>{loss_count}</span>",
                    unsafe_allow_html=True,
                )

            # Display everything as a Plotly chart in Streamlit
            # fig = make_subplots(rows=2, cols=1, shared_xaxes=True)
            fig = go.Figure()
            fig.add_trace(
                go.Scatter(
                    x=data["timestamp"],
                    y=data["close"],
                    mode="lines",
                    name=symbol + " Price",
                    yaxis="y",
                )
            )
            count = 0
            for i, (start_date, end_date) in enumerate(
                zip(start_dates, end_dates), start=1
            ):
                filtered_df = data[
                    (data["timestamp"] >= start_date)
                    & (data["timestamp"] <= end_date)
                ]
                fig.add_trace(
                    go.Scatter(
                        x=filtered_df["timestamp"],
                        y=filtered_df["close"],
                        mode="markers",
                        name=(
                            f'{start_date.strftime("%Y-%m-%d")} --'
                            f'{end_date.strftime("%Y-%m-%d")}'
                        ),
                        yaxis="y",
                        visible=True if count < 0 else "legendonly",
                    )
                )
                count += 1

            fig.update_layout(
                xaxis=dict(title="Timestamp"),
                yaxis=dict(
                    title=symbol + " Price",
                    side="left",
                    showgrid=False,
                    zeroline=False,
                ),
                legend=dict(x=0.01, y=0.99),
                height=700,
            )

            st.plotly_chart(fig, use_container_width=True)
