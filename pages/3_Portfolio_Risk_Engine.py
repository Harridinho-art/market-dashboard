import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np

# --- PAGE SETUP ---
st.set_page_config(page_title="Portfolio Risk Engine", layout="wide")
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
with st.spinner("Executing risk algorithms and fetching 10-year market data..."):
    # Download 10 years of data to capture the 2020 COVID crash, plus S&P 500 (^GSPC) for the Beta proxy
    download_tickers = tickers + ['^GSPC']
    raw_data = yf.download(download_tickers, period="10y", progress=False)['Close']
    
    if isinstance(raw_data, pd.Series):
        raw_data = raw_data.to_frame(download_tickers[0])
        
    daily_returns = raw_data.pct_change().dropna()
    
    # Isolate Market Returns (S&P 500) and Portfolio Returns
    market_returns = daily_returns['^GSPC'] if '^GSPC' in daily_returns.columns else None
    
    # Ensure we only use the portfolio tickers for the portfolio math
    available_tickers = [t for t in tickers if t in daily_returns.columns]
    
    if not available_tickers:
        st.error("Could not fetch data for the provided tickers.")
        st.stop()
        
    # Re-normalize weights if some tickers failed to download
    clean_weights = np.array([weights[tickers.index(t)] for t in available_tickers])
    clean_weights = clean_weights / np.sum(clean_weights)
    
    portfolio_returns = daily_returns[available_tickers].dot(clean_weights)
    
    # Calculate Portfolio Beta (Risk relative to the broader market)
    if market_returns is not None:
        cov_matrix = np.cov(portfolio_returns, market_returns)
        portfolio_beta = cov_matrix[0, 1] / cov_matrix[1, 1] if cov_matrix[1, 1] != 0 else 1.0
    else:
        portfolio_beta = 1.0
    
    # Core Risk Metrics
    var_95 = np.percentile(portfolio_returns, 5)
    cash_var_95 = portfolio_capital * abs(var_95)
    
    # Annualized Performance Metrics (252 trading days)
    ann_return = portfolio_returns.mean() * 252
    ann_volatility = portfolio_returns.std() * np.sqrt(252)
    risk_free_rate = 0.042  # 4.2% Benchmark
    
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
        help="Worst loss experienced from historical peak to trough over the last 10 years."
    )

# --- 4. HISTORICAL CRISIS STRESS-TESTING ---
st.divider()
st.subheader("3. Historical Stress-Testing (Macro Scenario Simulation)")
st.caption(f"Estimated capital destruction during major market crashes. Pre-2016 crises are simulated using the portfolio's current Beta correlation ({portfolio_beta:.2f}) against historical S&P 500 drawdowns.")

scenarios = []

# 1. Dot-Com Bubble (Simulated via Beta)
# S&P 500 dropped ~49.1% from Mar 2000 to Oct 2002
dot_com_impact = -0.491 * portfolio_beta
scenarios.append({
    "Macro Scenario": "2000 Dot-Com Bubble Collapse (Mar 2000 – Oct 2002)",
    "Observed / Simulated Impact (%)": f"{dot_com_impact * 100:.2f}%",
    "Estimated Capital Loss": f"${(portfolio_capital * abs(dot_com_impact)):,.0f}",
    "Data Source": "Beta Proxy (Simulated)"
})

# 2. Global Financial Crisis (Simulated via Beta)
# S&P 500 dropped ~56.8% from Oct 2007 to Mar 2009
gfc_impact = -0.568 * portfolio_beta
scenarios.append({
    "Macro Scenario": "2008 Global Financial Crisis (Oct 2007 – Mar 2009)",
    "Observed / Simulated Impact (%)": f"{gfc_impact * 100:.2f}%",
    "Estimated Capital Loss": f"${(portfolio_capital * abs(gfc_impact)):,.0f}",
    "Data Source": "Beta Proxy (Simulated)"
})

# 3. COVID-19 Flash Crash (Actual Data)
covid_crash = portfolio_returns.loc['2020-02-19':'2020-03-23'] if '2020-02-19' in portfolio_returns.index else pd.Series(dtype=float)
if not covid_crash.empty:
    covid_drawdown = (1 + covid_crash).cumprod().iloc[-1] - 1
    scenarios.append({
        "Macro Scenario": "2020 COVID-19 Flash Crash (Feb 2020 – Mar 2020)",
        "Observed / Simulated Impact (%)": f"{covid_drawdown * 100:.2f}%",
        "Estimated Capital Loss": f"${(portfolio_capital * abs(covid_drawdown)):,.0f}",
        "Data Source": "Actual Portfolio Data"
    })

# 4. 2022 Inflation & Rate Hike Shock (Actual Data)
rate_hike_2022 = portfolio_returns.loc['2022-01-03':'2022-10-14'] if '2022-01-03' in portfolio_returns.index else pd.Series(dtype=float)
if not rate_hike_2022.empty:
    rate_drawdown = (1 + rate_hike_2022).cumprod().iloc[-1] - 1
    scenarios.append({
        "Macro Scenario": "2022 Global Inflation Shock (Jan 2022 – Oct 2022)",
        "Observed / Simulated Impact (%)": f"{rate_drawdown * 100:.2f}%",
        "Estimated Capital Loss": f"${(portfolio_capital * abs(rate_drawdown)):,.0f}",
        "Data Source": "Actual Portfolio Data"
    })

# 5. Hypothetical Flash Crash
scenarios.append({
    "Macro Scenario": "Hypothetical Instant Market Shock (-10% Index Crash)",
    "Observed / Simulated Impact (%)": f"{-10.0 * portfolio_beta:.2f}%",
    "Estimated Capital Loss": f"${(portfolio_capital * abs(0.10 * portfolio_beta)):,.0f}",
    "Data Source": "Beta Proxy (Simulated)"
})

df_scenarios = pd.DataFrame(scenarios).set_index("Macro Scenario")
st.table(df_scenarios)

# --- 5. ESG & STEWARDSHIP SCREENING ---
st.divider()
st.subheader("4. ESG & Sustainability Risk Matrix")
st.caption("Responsible investment screening aligned with institutional mandates (e.g., CRISA 2, UN PRI). Simulated proxy scores demonstrate terminal architecture.")

esg_records = []
weighted_esg_total = 0.0

# Generate consistent deterministic proxy data per ticker
for t, w in zip(available_tickers, clean_weights):
    seed = sum(ord(c) for c in t)
    np.random.seed(seed)
    e_score = round(np.random.uniform(5, 20), 1)
    s_score = round(np.random.uniform(5, 20), 1)
    g_score = round(np.random.uniform(5, 15), 1)
    total = round(e_score + s_score + g_score, 1)
    
    weighted_esg_total += total * w
    
    esg_records.append({
        "Ticker": t,
        "Weight": f"{w*100:.1f}%",
        "Environmental": e_score,
        "Social": s_score,
        "Governance": g_score,
        "Total ESG Risk": total
    })

df_esg = pd.DataFrame(esg_records).set_index("Ticker")

# Portfolio Weighted Metric Card
esg_col1, esg_col2 = st.columns([1, 2])
with esg_col1:
    st.metric(
        "Portfolio Weighted ESG Risk", 
        f"{weighted_esg_total:.1f}", 
        help="Sustainalytics scale: 0-10 Negligible, 10-20 Low, 20-30 Medium, 30-40 High, 40+ Severe."
    )

# Heatmap Table (Lower score = Green, Higher risk = Red)
st.dataframe(
    df_esg.style.background_gradient(cmap="RdYlGn_r", subset=["Environmental", "Social", "Governance", "Total ESG Risk"]),
    use_container_width=True
)