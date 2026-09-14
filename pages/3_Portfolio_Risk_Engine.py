import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from scipy.stats import gaussian_kde

st.title("Portfolio Risk & Macro Stress Engine")
st.caption("Institutional capital preservation, Value-at-Risk (VaR), and historical crisis stress-testing.")

# --- 1. PORTFOLIO ALLOCATION & CAPITAL ---
st.subheader("1. Portfolio Construction & Capital Base")

col1, col2, col3 = st.columns([2, 2, 1.5])
with col1:
    tickers_input = st.text_input("Portfolio Tickers (comma-separated):", value="AAPL, MSFT, TSLA, JNJ")
with col2:
    weights_input = st.text_input("Portfolio Weights (%) (must total 100):", value="35, 30, 15, 20")
with col3:
    portfolio_capital = st.number_input("Portfolio Value ($ / R):", value=1_000_000, step=100_000)

# Parsing & Validation
tickers = [t.strip().upper() for t in tickers_input.split(',') if t.strip()]
try:
    weights = np.array([float(w.strip()) / 100 for w in weights_input.split(',') if w.strip()])
except ValueError:
    st.error("Please enter valid numerical values for weights.")
    st.stop()

if len(tickers) != len(weights):
    st.error("The count of tickers must match the count of weights.")
    st.stop()

if not np.isclose(sum(weights), 1.0):
    weights = weights / np.sum(weights)
    st.info("Weights normalized automatically to 100%.")

# --- 2. DATA ACQUISITION & ENGINE MATH ---
with st.spinner("Executing risk algorithms across historical datasets..."):
    # Download 5 years of daily closing prices
    raw_data = yf.download(tickers, period="5y", progress=False)['Close']
    
    if isinstance(raw_data, pd.Series):
        raw_data = raw_data.to_frame(tickers[0])
        
    daily_returns = raw_data.pct_change().dropna()
    
    # Portfolio daily returns series
    portfolio_returns = daily_returns.dot(weights)
    
    # Core Risk Metrics
    var_95 = np.percentile(portfolio_returns, 5)
    cash_var_95 = portfolio_capital * abs(var_95)
    
    # Annualized Performance Metrics (252 trading days)
    ann_return = portfolio_returns.mean() * 252
    ann_volatility = portfolio_returns.std() * np.sqrt(252)
    risk_free_rate = 0.042  # 4.2% Benchmark
    
    sharpe_ratio = (ann_return - risk_free_rate) / ann_volatility if ann_volatility else 0
    
    # Downside deviation for Sortino Ratio
    downside_returns = portfolio_returns[portfolio_returns < 0]
    downside_volatility = downside_returns.std() * np.sqrt(252)
    sortino_ratio = (ann_return - risk_free_rate) / downside_volatility if downside_volatility else 0
    
    # Maximum Drawdown
    cumulative_growth = (1 + portfolio_returns).cumprod()
    peak = cumulative_growth.cummax()
    drawdowns = (cumulative_growth - peak) / peak
    max_drawdown = drawdowns.min()

# --- 3. EXECUTIVE RISK SUMMARY ---
st.divider()
st.subheader("2. Enterprise Risk & Downside Exposure")

m_col1, m_col2, m_col3, m_col4 = st.columns(4)
with m_col1:
    st.metric(
        "Historical 1-Day VaR (95%)", 
        f"{var_95 * 100:.2f}%", 
        help="In 95% of trading days, daily loss will not exceed this percentage."
    )
with m_col2:
    st.metric(
        "1-Day Cash at Risk", 
        f"${cash_var_95:,.0f}", 
        help="Maximum expected capital loss over a single trading day at 95% confidence."
    )
with m_col3:
    st.metric(
        "Sortino Ratio", 
        f"{sortino_ratio:.2f}", 
        help="Return per unit of bad (downside) volatility. > 1.0 indicates strong risk control."
    )
with m_col4:
    st.metric(
        "Max Peak-to-Trough Drawdown", 
        f"{max_drawdown * 100:.2f}%", 
        help="Worst loss experienced from historical peak to trough over 5 years."
    )

# --- 4. INTERACTIVE PLOTLY DISTRIBUTION (TAIL RISK) ---
st.divider()
st.subheader("3. Interactive Tail-Risk Distribution")
st.caption("Hover over the distribution curve to inspect frequencies. Shaded crimson area highlights extreme tail-risk loss days.")

# Generate KDE Curve
kde = gaussian_kde(portfolio_returns * 100)
x_range = np.linspace((portfolio_returns * 100).min(), (portfolio_returns * 100).max(), 500)
y_density = kde(x_range)

fig = go.Figure()

# Plot full density curve
fig.add_trace(go.Scatter(
    x=x_range, 
    y=y_density, 
    mode='lines', 
    line=dict(color='#2563eb', width=2.5), 
    name='Return Distribution'
))

# Shade Tail Risk Zone (< VaR 95%)
x_tail = x_range[x_range <= (var_95 * 100)]
y_tail = y_density[:len(x_tail)]
fig.add_trace(go.Scatter(
    x=np.concatenate(([x_tail[0]], x_tail, [x_tail[-1]])),
    y=np.concatenate(([0], y_tail, [0])),
    fill='toself',
    fillcolor='rgba(239, 68, 68, 0.4)',
    line=dict(color='rgba(239, 68, 68, 0.8)', width=1.5),
    name=f'Tail Risk Zone (95% VaR: {var_95*100:.2f}%)'
))

# VaR Cutoff Threshold Line
fig.add_vline(
    x=var_95 * 100, 
    line_dash="dash", 
    line_color="#dc2626", 
    annotation_text=f"VaR Cutoff: {var_95*100:.2f}%", 
    annotation_position="top left"
)

fig.update_layout(
    xaxis_title="Daily Return (%)",
    yaxis_title="Probability Density",
    margin=dict(l=20, r=20, t=30, b=20),
    template="plotly_white",
    hovermode="x unified",
    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
)

st.plotly_chart(fig, use_container_width=True)

# --- 5. HISTORICAL CRISIS STRESS-TESTING ---
st.divider()
st.subheader("4. Historical Stress-Testing (Scenario Simulation)")
st.caption("Estimated portfolio impact during recognized macroeconomic drawdown regimes.")

# Filter returns by historical crisis windows
covid_crash = portfolio_returns.loc['2020-02-19':'2020-03-23'] if '2020-02-19' in portfolio_returns.index else pd.Series(dtype=float)
rate_hike_2022 = portfolio_returns.loc['2022-01-03':'2022-10-14'] if '2022-01-03' in portfolio_returns.index else pd.Series(dtype=float)

scenarios = []

# COVID Crash Impact
if not covid_crash.empty:
    covid_drawdown = ((1 + covid_crash).cumprod().iloc[-1] - 1) * 100
    scenarios.append({
        "Macro Scenario": "2020 COVID-19 Flash Crash (Feb–Mar 2020)",
        "Observed Impact (%)": f"{covid_drawdown:.2f}%",
        "Estimated Capital Loss": f"${(portfolio_capital * abs(covid_drawdown)/100):,.0f}"
    })

# 2022 Rate Shock Impact
if not rate_hike_2022.empty:
    rate_drawdown = ((1 + rate_hike_2022).cumprod().iloc[-1] - 1) * 100
    scenarios.append({
        "Macro Scenario": "2022 Inflation & Rate Hike Shock (Jan–Oct 2022)",
        "Observed Impact (%)": f"{rate_drawdown:.2f}%",
        "Estimated Capital Loss": f"${(portfolio_capital * abs(rate_drawdown)/100):,.0f}"
    })

# Instant Shock Simulation
scenarios.append({
    "Macro Scenario": "Hypothetical Instant Market Shock (-5% Index Crash)",
    "Observed Impact (%)": "-5.00%",
    "Estimated Capital Loss": f"${(portfolio_capital * 0.05):,.0f}"
})

df_scenarios = pd.DataFrame(scenarios).set_index("Macro Scenario")
st.table(df_scenarios)