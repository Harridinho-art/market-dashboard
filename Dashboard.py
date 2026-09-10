import streamlit as st
import pandas as pd
import plotly.express as px
import yfinance as yf

st.set_page_config(page_title="Dashboard", page_icon=":bar_chart:", layout="wide")
st.title("📈 Live Market Dashboard")
st.write("Welcome to the financial data hub. Let's pull some market data and visualize it in real-time.")

tickers_input = st.text_input("Enter stock tickers (comma-separated):", "AAPL, MSFT, GOOGL")
tickers = [ticker.strip().upper() for ticker in tickers_input.split(",") if ticker.strip()]

if tickers:
    try:
        data = yf.download(tickers, period="6mo")
        
        if not data.empty:
            close_prices = data['Close']
            if isinstance(close_prices, pd.Series):
                close_prices = close_prices.to_frame(name=tickers[0])
                
            st.subheader("6-Month Executive Summary")
            cols = st.columns(len(tickers))
            
            for i, ticker in enumerate(tickers):
                if ticker in close_prices.columns:
                    start_price = close_prices[ticker].dropna().iloc[0]
                    end_price = close_prices[ticker].dropna().iloc[1] if len(close_prices[ticker].dropna()) > 1 else start_price
                    pct_change = ((end_price - start_price) / start_price) * 100
                    
                    with cols[i]:
                        st.metric(label=ticker, value=f"{end_price:.2f}", delta=f"{pct_change:.2f}%")
                        
            st.subheader("Normalized Growth (%)")
            normalized_prices = (close_prices / close_prices.iloc[0] - 1) * 100
            fig = px.line(normalized_prices, title="Growth Trajectory (Rebased to 0%)", labels={'value': 'Cumulative Return (%)', 'variable': 'Ticker'})
            st.plotly_chart(fig, use_container_width=True)
            
            with st.expander("View & Download Raw Data (Bypass Paywall)"):
                st.dataframe(close_prices)
                csv = close_prices.to_csv().encode('utf-8')
                st.download_button(
                    label="📥 Download Data as CSV",
                    data=csv,
                    file_name="stock_data.csv",
                    mime="text/csv"
                )
        else:
            st.error("No data found. Please check the ticker symbols.")
            
    except Exception as e:
        st.error(f"An error occurred while fetching data: {e}") 