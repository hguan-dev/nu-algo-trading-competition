import json
import pandas as pd
import matplotlib.pyplot as plt

# Read the JSON file
with open('orders_per_type_1s.json', 'r') as file:
    json_data = file.read()

# Parse the JSON data
data = json.loads(json_data)

# Initialize an empty list to store data
data_list = []

# Check if the status is 'success'
if data.get('status') == 'success':
    # Extract the results
    results = data['data']['result']
    for result in results:
        metric = result['metric']
        trader_type = metric.get('trader_type', 'UNKNOWN')
        values = result['values']
        for value_pair in values:
            timestamp = int(value_pair[0])
            value = float(value_pair[1])
            data_list.append({
                'trader_type': trader_type,
                'timestamp': timestamp,
                'value': value
            })
else:
    print("Failed to retrieve data.")

# Create a DataFrame
df = pd.DataFrame(data_list)

# Convert timestamp to datetime
df['datetime'] = pd.to_datetime(df['timestamp'], unit='s')

# Set the datetime as the index
df.set_index('datetime', inplace=True)

# Drop the timestamp column
df.drop('timestamp', axis=1, inplace=True)

# Display the first few rows
print(df.head())

# Check unique trader types
trader_types = df['trader_type'].unique()
print(f"Trader types in data: {trader_types}")

# If multiple trader types, pivot the DataFrame
if len(trader_types) > 1:
    df_pivot = df.pivot(columns='trader_type', values='value')
    # Plot values for each trader type
    df_pivot.plot(figsize=(12, 6))
    plt.title('Orders per Second by Trader Type')
    plt.xlabel('Time')
    plt.ylabel('Value')
    plt.grid(True)
    plt.legend(title='Trader Type')
    plt.show()
else:
    # Plot the value over time
    plt.figure(figsize=(12, 6))
    plt.plot(df.index, df['value'], marker='o', linestyle='-')
    plt.title(f"Orders per Second for Trader Type: {trader_types[0]}")
    plt.xlabel('Time')
    plt.ylabel('Value')
    plt.grid(True)
    plt.show()
