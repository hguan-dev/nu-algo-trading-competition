import json
import pandas as pd
import matplotlib.pyplot as plt


def parse_matches_by_type(json_file_path):
    with open(json_file_path, 'r') as file:
        json_data = file.read()
    
    data = json.loads(json_data)
    data_list = []
    
    if data.get('status') == 'success':
        results = data['data']['result']
        for result in results:
            metric = result['metric']
            match_type = metric.get('match_type', 'UNKNOWN')
            values = result['values']
            for value_pair in values:
                timestamp = int(value_pair[0])
                match_value = float(value_pair[1])
                data_list.append({
                    'match_type': match_type,
                    'timestamp': timestamp,
                    'match_value': match_value
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

def plot_matches_by_type(df):
    match_types = df['match_type'].unique()
    if len(match_types) > 1:
        # Pivot the DataFrame
        df_pivot = df.pivot(columns='match_type', values='match_value')
        # Plot the data
        df_pivot.plot(figsize=(12, 6))
        plt.title('Matches by Type Over Time')
        plt.xlabel('Time')
        plt.ylabel('Match Value')
        plt.grid(True)
        plt.legend(title='Match Type')
        plt.show()
    else:
        plt.figure(figsize=(12, 6))
        plt.plot(df.index, df['match_value'], marker='o', linestyle='-')
        plt.title(f"Matches Over Time for Match Type: {match_types[0]}")
        plt.xlabel('Time')
        plt.ylabel('Match Value')
        plt.grid(True)
        plt.show()
