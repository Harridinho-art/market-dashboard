import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import datetime

st.title("Portfolio Risk & ESG Optimizer")
st.markdown("Institutional-grade portfolio analytics, downside risk (VaR), and sustainability tracking.")

# --- PORTFOLIO CONSTRUCTION ---
st.subheader("1. Portfolio Construction")
col1, col2 = st.columns(2)
with col1:
    tickers_input = st.text_input("Enter Tickers (comma-separated):", "AAPL, MSFT, TSLA, JNJ")
with col2:
    weights_input = st.text_input("Enter Weights (%) (must total 100):", "40, 30, 20, 10")

# Clean inputs
tickers = [t.strip().upper() for t in tickers_input.split(',')]
try:
    weights = np.array([float(w.strip())/100 for w in weights_input.split(',')])
except:
    st.error("Please enter valid numbers for weights.")
    st.stop()

if len(tickers) != len(weights):
    st.error("The number of tickers must match the number of weights.")
    st.stop()

if not np.isclose(sum(weights), 1.0):
    st.warning("Weights do not equal 100%. Automatically normalizing...")
    weights = weights / np.sum(weights)

# --- DATA FETCHING & MATH ---
with st.spinner("Fetching 5-year historical data & computing covariance matrices..."):
    # Download historical close prices
    data = yf.download(tickers, period="5y")['Close']
    
    # If only one ticker is entered, yf.download returns a Series. Convert to DataFrame.
    if isinstance(data, pd.Series):
        data = data.to_frame(tickers[0])
        
    # Calculate daily returns and drop NAs
    returns = data.pct_change().dropna()
    
    # Portfolio historical daily returns
    port_returns = returns.dot(weights)
    
    # --- RISK MATH ---
    # 1. Historical Value at Risk (95% Confidence)
    var_95 = np.percentile(port_returns, 5)
    
    # 2. Maximum Drawdown
    cumulative_returns = (1 + port_returns).cumprod()
    peak = cumulative_returns.cummax()
    drawdown = (cumulative_returns - peak) / peak
    max_drawdown = drawdown.min()
    
    # 3. Annualized Volatility
    ann_volatility = port_returns.std() * np.sqrt(252)

# --- ENTERPRISE RISK METRICS ---
st.divider()
st.subheader("2. Enterprise Risk Metrics")
st.caption("Evaluating capital preservation and downside exposure.")

rm_col1, rm_col2, rm_col3 = st.columns(3)
with rm_col1:
    st.metric("Historical VaR (95%)", f"{var_95*100:.2f}%", help="In 95% of trading days, the portfolio will not lose more than this percentage.")
with rm_col2:
    st.metric("Maximum Drawdown", f"{max_drawdown*100:.2f}%", help="The absolute worst peak-to-trough drop over the last 5 years.")
with rm_col3:
    st.metric("Annualized Volatility", f"{ann_volatility*100:.2f}%", help="Standard deviation of annualized returns.")

# --- TAIL RISK VISUALIZATION ---
st.divider()
st.subheader("3. Daily Returns Distribution (Tail Risk)")
st.caption("The red line indicates the 95% VaR threshold. Everything to the left is a tail-risk event.")

fig, ax = plt.subplots(figsize=(10, 4))
# Plot histogram of returns
ax.hist(port_returns * 100, bins=50, color='#3b82f6', alpha=0.7, edgecolor='black')

# Add VaR line
ax.axvline(var_95 * 100, color='red', linestyle='dashed', linewidth=2, label=f'95% VaR ({var_95*100:.2f}%)')

ax.set_title("Portfolio Historical Return Distribution", fontsize=12)
ax.set_xlabel("Daily Return (%)")
ax.set_ylabel("Frequency (Days)")
ax.legend()

st.pyplot(fig)

# --- ESG & SUSTAINABILITY ---
st.divider()
st.subheader("4. ESG & Sustainability Risk Matrix")
st.caption("Note: Live institutional ESG scoring generally requires a Bloomberg/Refinitiv terminal. This UI demonstrates the screening architecture using simulated API fallbacks.")

# Generate proxy ESG data to demonstrate the UI structure
esg_data = []
for i, t in enumerate(tickers):
    # Static seed ensures the proxy data stays consistent when you change weights
    np.random.seed(len(t) + i) 
    env_score = np.random.uniform(5, 20)
    soc_score = np.random.uniform(5, 20)
    gov_score = np.random.uniform(5, 15)
    
    esg_data.append({
        "Ticker": t,
        "Environment Risk": env_score,
        "Social Risk": soc_score,
        "Governance Risk": gov_score,
        "Total ESG Risk": env_score + soc_score + gov_score
    })
    
df_esg = pd.DataFrame(esg_data).set_index("Ticker")

# Highlight lower risk (better) in green, higher risk in red
st.dataframe(
    df_esg.style.background_gradient(cmap="RdYlGn_r", axis=0).format("{:.1f}"),
    use_container_width=True
)