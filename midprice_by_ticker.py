import json
import pandas as pd
import matplotlib.pyplot as plt

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

def plot_midprice_by_ticker(df):
    tickers = df['ticker'].unique()
    if len(tickers) > 1:
        # Pivot the DataFrame
        df_pivot = df.pivot(columns='ticker', values='midprice')
        # Plot the data
        df_pivot.plot(figsize=(12, 6))
        plt.title('Midprice by Ticker Over Time')
        plt.xlabel('Time')
        plt.ylabel('Midprice')
        plt.grid(True)
        plt.legend(title='Ticker')
        plt.show()
    else:
        plt.figure(figsize=(12, 6))
        plt.plot(df.index, df['midprice'], marker='o', linestyle='-')
        plt.title(f"Midprice Over Time for Ticker: {tickers[0]}")
        plt.xlabel('Time')
        plt.ylabel('Midprice')
        plt.grid(True)
        plt.show()

# Parse the midprice by ticker data
df_midprice = parse_midprice_by_ticker('midprice_by_ticker_1s.json')

if df_midprice is not None:
    # Display the first few rows
    print(df_midprice.head())
    # Plot the midprice by ticker
    plot_midprice_by_ticker(df_midprice)
