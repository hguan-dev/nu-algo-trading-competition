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

def plot_midprice_with_rsi(df):
    # Calculate RSI for each ticker
    df['RSI'] = df.groupby('ticker')['midprice'].apply(lambda x: ta.momentum.RSIIndicator(x, window=14).rsi()).reset_index(level=0, drop=True)
    
    # Plot the data
    fig, axes = plt.subplots(nrows=2, ncols=1, figsize=(14, 10), sharex=True)
    
    # Plot Midprice
    tickers = df['ticker'].unique()
    for ticker in tickers:
        ticker_df = df[df['ticker'] == ticker].tail(200)
        print(f"Last 200 data points for {ticker} (Midprice):")
        print(ticker_df[['midprice']].tail(200)) 
        axes[0].plot(ticker_df.index, ticker_df['midprice'], label=f'Midprice - {ticker}')
        df[df['ticker'] == ticker].tail(200)
        break
    
    
    axes[0].set_title('Midprice for Different Tickers (Last 200 Data Points)')
    axes[0].set_ylabel('Price')
    axes[0].legend()
    axes[0].grid(True)
    
    # Plot RSI
    for ticker in tickers:
        ticker_df = df[df['ticker'] == ticker].tail(200)
        print(f"Last 50 data points for {ticker} (RSI):")
        print(ticker_df[['RSI']].tail(200))  
        axes[1].plot(ticker_df.index, ticker_df['RSI'], label=f'RSI - {ticker}')
        break
    
    axes[1].set_title('RSI for Different Tickers (Last 200 Data Points)')
    axes[1].set_ylabel('RSI Value')
    axes[1].axhline(70, color='red', linestyle='--', label='Overbought (70)')
    axes[1].axhline(30, color='green', linestyle='--', label='Oversold (30)')
    axes[1].legend()
    axes[1].grid(True)
    
    plt.xlabel('Time')
    plt.tight_layout()
    plt.show()


# Parse the midprice by ticker data
df_midprice = parse_midprice_by_ticker('midprice_by_ticker_1s.json')

if df_midprice is not None:
    # Display the first few rows
    print()
    print(df_midprice.head())
    # Plot the midprice with RSI
    plot_midprice_with_rsi(df_midprice)
