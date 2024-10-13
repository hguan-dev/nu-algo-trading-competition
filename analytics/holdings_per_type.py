import json
import pandas as pd
import matplotlib.pyplot as plt

def parse_holdings_per_type(json_file_path):
    with open(json_file_path, 'r') as file:
        json_data = file.read()
    
    data = json.loads(json_data)
    data_list = []
    
    if data.get('status') == 'success':
        results = data['data']['result']
        for result in results:
            metric = result['metric']
            trader_type = metric.get('trader_type', 'UNKNOWN')
            values = result['values']
            for value_pair in values:
                timestamp = int(value_pair[0])
                holding_value = float(value_pair[1])
                data_list.append({
                    'trader_type': trader_type,
                    'timestamp': timestamp,
                    'holding_value': holding_value
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


def plot_holdings_per_type(df):
    trader_types = df['trader_type'].unique()
    if len(trader_types) > 1:
        # Pivot the DataFrame
        df_pivot = df.pivot(columns='trader_type', values='holding_value')
        # Plot the data
        df_pivot.plot(figsize=(12, 6))
        plt.title('Holdings per Type Over Time')
        plt.xlabel('Time')
        plt.ylabel('Holding Value')
        plt.grid(True)
        plt.legend(title='Trader Type')
        plt.show()
    else:
        plt.figure(figsize=(12, 6))
        plt.plot(df.index, df['holding_value'], marker='o', linestyle='-')
        plt.title(f"Holdings Over Time for Trader Type: {trader_types[0]}")
        plt.xlabel('Time')
        plt.ylabel('Holding Value')
        plt.grid(True)
        plt.show()

if __name__ == '__main__':
    # Parse the holdings per type data
    df_holdings = parse_holdings_per_type('holdings_per_type_1s.json')

    if df_holdings is not None:
        # Display the first few rows
        print(df_holdings.head())
        # Plot the holdings per type
        plot_holdings_per_type(df_holdings)
