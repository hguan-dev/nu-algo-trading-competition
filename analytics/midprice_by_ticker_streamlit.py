import json
import pandas as pd
import streamlit as st
import plotly.graph_objects as go
import ta

# Function to parse midprice from JSON
def parse_midprice_by_ticker(file_content):
    # Convert bytes content into string and load as JSON
    json_data = json.loads(file_content)
    
    data_list = []
    
    if json_data.get('status') == 'success':
        results = json_data['data']['result']
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
        st.error('Failed to retrieve data.')
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

# Function to plot midprice and RSI using Plotly
def plot_midprice_with_rsi(df):
    # Calculate RSI for each ticker
    df['RSI'] = df.groupby('ticker')['midprice'].apply(lambda x: ta.momentum.RSIIndicator(x, window=14).rsi()).reset_index(level=0, drop=True)

    tickers = df['ticker'].unique()

    # Create Plotly figure with subplots
    fig = go.Figure()

    # Plot Midprice
    for ticker in tickers:
        ticker_df = df[df['ticker'] == ticker]
        fig.add_trace(go.Scatter(
            x=ticker_df.index, 
            y=ticker_df['midprice'], 
            mode='lines', 
            name=f'Midprice - {ticker}'
        ))

    # Add RSI plot in the same graph (secondary y-axis)
    for ticker in tickers:
        ticker_df = df[df['ticker'] == ticker]
        fig.add_trace(go.Scatter(
            x=ticker_df.index, 
            y=ticker_df['RSI'], 
            mode='lines', 
            name=f'RSI - {ticker}',
            yaxis="y2"
        ))

    # Customize layout for two y-axes
    fig.update_layout(
        title="Midprice and RSI for Different Tickers",
        xaxis_title="Time",
        yaxis_title="Midprice",
        yaxis2=dict(
            title="RSI",
            overlaying="y",
            side="right"
        ),
        legend=dict(orientation="h"),
        template="plotly_dark"
    )

    # Add horizontal lines for overbought/oversold levels
    fig.add_shape(type="line", x0=df.index.min(), y0=70, x1=df.index.max(), y1=70,
                  line=dict(color="red", dash="dash"), xref='x', yref='y2')
    fig.add_shape(type="line", x0=df.index.min(), y0=30, x1=df.index.max(), y1=30,
                  line=dict(color="green", dash="dash"), xref='x', yref='y2')

    st.plotly_chart(fig)

# Streamlit App Code
st.title("Midprice and RSI Analysis")

# Upload JSON file
uploaded_file = st.file_uploader("Choose a JSON file", type="json")

if uploaded_file is not None:
    df_midprice = parse_midprice_by_ticker(uploaded_file)

    if df_midprice is not None:
        st.write("Data Preview", df_midprice.head())
        # Plot Midprice and RSI using Plotly
        plot_midprice_with_rsi(df_midprice)
