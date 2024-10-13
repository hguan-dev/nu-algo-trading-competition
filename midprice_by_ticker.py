import json
import pandas as pd
import matplotlib.pyplot as plt
import ta

def parse_midprice_by_ticker(json_file_path):
    with open(json_file_path, 'r') as file:
        json_data = file.read()
    
    data = json.loads(json_data)
    data_list = []
    
    if data.get('status') == 'success':
        results = data['data']['result']
        for result in results:
            metric = result['metric']
            ticker = metric.get('ticker', 'UNKNOWN')
            values = result['values']
            for value_pair in values:
                timestamp = int(value_pair[0])
                midprice = float(value_pair[1])
                data_list.append({
                    'ticker': ticker,
                    'timestamp': timestamp,
                    'midprice': midprice
                })
    else:
        print('Failed to retrieve data.')
        return None
    
    # Create a DataFrame
    df = pd.DataFrame(data_list)
    
    # Convert timestamp to datetime
    df['datetime'] = pd.to_datetime(df['timestamp'], unit='s')
    
    # Set the datetime as the index
    df.set_index('datetime', inplace=True)
    
    # Drop the timestamp column
    df.drop('timestamp', axis=1, inplace=True)
    
    return df

def plot_midprice_with_indicators(df):
    # Calculate technical indicators
    df['RSI'] = ta.momentum.RSIIndicator(df['midprice'], window=14).rsi()
    df['MA_10'] = ta.trend.SMAIndicator(df['midprice'], window=10).sma_indicator()
    df['EMA_10'] = ta.trend.EMAIndicator(df['midprice'], window=10).ema_indicator()
    
    bollinger = ta.volatility.BollingerBands(df['midprice'], window=10, window_dev=2)
    df['Bollinger_High'] = bollinger.bollinger_hband()
    df['Bollinger_Low'] = bollinger.bollinger_lband()
    
    macd = ta.trend.MACD(df['midprice'])
    df['MACD'] = macd.macd()
    df['MACD_Signal'] = macd.macd_signal()
    df['MACD_Diff'] = macd.macd_diff()
    
    # Plot the data
    fig, axes = plt.subplots(nrows=3, ncols=1, figsize=(14, 10), sharex=True)
    
    # Plot Midprice with Moving Averages and Bollinger Bands
    axes[0].plot(df.index, df['midprice'], label='Midprice', color='blue')
    axes[0].plot(df.index, df['MA_10'], label='MA 10', color='orange')
    axes[0].plot(df.index, df['EMA_10'], label='EMA 10', color='green')
    axes[0].fill_between(df.index, df['Bollinger_Low'], df['Bollinger_High'], color='lightgray', alpha=0.5, label='Bollinger Bands')
    axes[0].set_title('Midprice with MA, EMA, and Bollinger Bands')
    axes[0].set_ylabel('Price')
    axes[0].legend()
    
    # Plot MACD
    axes[1].plot(df.index, df['MACD'], label='MACD', color='purple')
    axes[1].plot(df.index, df['MACD_Signal'], label='Signal Line', color='red')
    axes[1].bar(df.index, df['MACD_Diff'], label='MACD Histogram', color='grey')
    axes[1].set_title('MACD')
    axes[1].set_ylabel('MACD Value')
    axes[1].legend()
    
    # Plot RSI
    axes[2].plot(df.index, df['RSI'], label='RSI', color='brown')
    axes[2].axhline(70, color='red', linestyle='--', label='Overbought (70)')
    axes[2].axhline(30, color='green', linestyle='--', label='Oversold (30)')
    axes[2].set_title('Relative Strength Index (RSI)')
    axes[2].set_ylabel('RSI Value')
    axes[2].legend()
    
    plt.xlabel('Time')
    plt.tight_layout()
    plt.show()

# Parse the midprice by ticker data
df_midprice = parse_midprice_by_ticker('midprice_by_ticker_1s.json')

if df_midprice is not None:
    # Display the first few rows
    print(df_midprice.head())
    # Plot the midprice with indicators
    plot_midprice_with_indicators(df_midprice)
