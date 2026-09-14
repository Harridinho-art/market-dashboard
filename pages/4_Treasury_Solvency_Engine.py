import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots

st.set_page_config(page_title="Treasury Engine", layout="wide")
st.title("Corporate Treasury & Solvency Engine")
st.markdown("Live liquidity stress-testing, DuPont ROE decomposition, and Altman Z-Score bankruptcy prediction.")

# --- 1. UNIVERSAL INPUTS & MACRO SHOCKS ---
st.sidebar.header("War Room Parameters")
ticker_a = st.sidebar.text_input("Company A Ticker (e.g., AAL.L, AAPL):", value="AAPL").upper()
ticker_b = st.sidebar.text_input("Company B Ticker (e.g., GLEN.L, MSFT):", value="MSFT").upper()

st.sidebar.divider()
st.sidebar.subheader("Macroeconomic Shocks")
rev_shock = st.sidebar.slider("Revenue Shock (%)", min_value=-100, max_value=20, value=-25, step=5)
rate_shock_bps = st.sidebar.slider("Interest Rate Shock (bps)", min_value=0, max_value=500, value=150, step=25) / 10000

# --- DATA ACQUISITION ENGINE ---
@st.cache_data(ttl=3600)
def fetch_treasury_data(ticker):
    try:
        t = yf.Ticker(ticker)
        bs = t.balance_sheet
        inc = t.income_stmt
        info = t.info
        
        # Safely extract latest financials (Fallback to 0 if missing to prevent crashes)
        total_assets = bs.loc['Total Assets'].iloc[0] if 'Total Assets' in bs.index else 1
        total_liab = bs.loc['Total Liabilities Net Minority Interest'].iloc[0] if 'Total Liabilities Net Minority Interest' in bs.index else 1
        current_assets = bs.loc['Current Assets'].iloc[0] if 'Current Assets' in bs.index else 0
        current_liab = bs.loc['Current Liabilities'].iloc[0] if 'Current Liabilities' in bs.index else 1
        cash = bs.loc['Cash And Cash Equivalents'].iloc[0] if 'Cash And Cash Equivalents' in bs.index else 0
        retained_earnings = bs.loc['Retained Earnings'].iloc[0] if 'Retained Earnings' in bs.index else 0
        total_debt = bs.loc['Total Debt'].iloc[0] if 'Total Debt' in bs.index else 0
        total_equity = bs.loc['Stockholders Equity'].iloc[0] if 'Stockholders Equity' in bs.index else 1
        
        revenue = inc.loc['Total Revenue'].iloc[0] if 'Total Revenue' in inc.index else 1
        ebit = inc.loc['EBIT'].iloc[0] if 'EBIT' in inc.index else 0
        net_income = inc.loc['Net Income'].iloc[0] if 'Net Income' in inc.index else 0
        interest_exp = abs(inc.loc['Interest Expense'].iloc[0]) if 'Interest Expense' in inc.index else 0
        tax_prov = inc.loc['Tax Provision'].iloc[0] if 'Tax Provision' in inc.index else 0
        pretax_income = inc.loc['Pretax Income'].iloc[0] if 'Pretax Income' in inc.index else 1
        
        market_cap = info.get('marketCap', total_assets)
        
        return {
            "Total Assets": total_assets, "Total Liab": total_liab, "Current Assets": current_assets,
            "Current Liab": current_liab, "Cash": cash, "Retained Earnings": retained_earnings,
            "Total Debt": total_debt, "Total Equity": total_equity, "Revenue": revenue, 
            "EBIT": ebit, "Net Income": net_income, "Interest Exp": interest_exp, 
            "Pretax Income": pretax_income, "Market Cap": market_cap
        }
    except Exception as e:
        return None

with st.spinner("Compiling institutional treasury data..."):
    data_a = fetch_treasury_data(ticker_a)
    data_b = fetch_treasury_data(ticker_b)

if not data_a or not data_b:
    st.error("Data retrieval failed for one or both tickers. Please verify the symbols (use '.L' for LSE stocks).")
    st.stop()

# --- 2. ALTMAN Z-SCORE (BANKRUPTCY PREDICTOR) ---
def calc_z_score(d):
    x1 = (d["Current Assets"] - d["Current Liab"]) / d["Total Assets"]
    x2 = d["Retained Earnings"] / d["Total Assets"]
    x3 = d["EBIT"] / d["Total Assets"]
    x4 = d["Market Cap"] / d["Total Liab"]
    x5 = d["Revenue"] / d["Total Assets"]
    return (1.2 * x1) + (1.4 * x2) + (3.3 * x3) + (0.6 * x4) + (1.0 * x5)

z_a = calc_z_score(data_a)
z_b = calc_z_score(data_b)

st.subheader("1. Altman Z-Score (Institutional Solvency)")
st.caption("A Z-Score > 2.99 indicates a safe zone. < 1.81 indicates high bankruptcy distress risk.")

fig_z = go.Figure()
fig_z.add_trace(go.Indicator(
    mode="number+gauge", value=z_a, title={'text': ticker_a},
    gauge={'axis': {'range': [0, 5]},
           'bar': {'color': "black"},
           'steps': [{'range': [0, 1.8], 'color': "#ef4444"},
                     {'range': [1.8, 3.0], 'color': "#facc15"},
                     {'range': [3.0, 5.0], 'color': "#22c55e"}]},
    domain={'x': [0, 0.45], 'y': [0, 1]}
))
fig_z.add_trace(go.Indicator(
    mode="number+gauge", value=z_b, title={'text': ticker_b},
    gauge={'axis': {'range': [0, 5]},
           'bar': {'color': "black"},
           'steps': [{'range': [0, 1.8], 'color': "#ef4444"},
                     {'range': [1.8, 3.0], 'color': "#facc15"},
                     {'range': [3.0, 5.0], 'color': "#22c55e"}]},
    domain={'x': [0.55, 1], 'y': [0, 1]}
))
fig_z.update_layout(height=300, margin=dict(t=50, b=0))
st.plotly_chart(fig_z, use_container_width=True)

# --- 3. THE 5-WAY DUPONT DECOMPOSITION ---
st.divider()
st.subheader("2. 5-Way DuPont ROE Analysis")
st.caption("Isolating exactly how management generates Return on Equity (Operating Efficiency vs. Financial Leverage).")

def calc_dupont(d):
    tax_burden = d["Net Income"] / d["Pretax Income"] if d["Pretax Income"] else 0
    int_burden = d["Pretax Income"] / d["EBIT"] if d["EBIT"] else 0
    op_margin = d["EBIT"] / d["Revenue"] if d["Revenue"] else 0
    asset_turnover = d["Revenue"] / d["Total Assets"] if d["Total Assets"] else 0
    leverage = d["Total Assets"] / d["Total Equity"] if d["Total Equity"] else 0
    roe = tax_burden * int_burden * op_margin * asset_turnover * leverage
    return [tax_burden, int_burden, op_margin, asset_turnover, leverage, roe]

dupont_a = calc_dupont(data_a)
dupont_b = calc_dupont(data_b)

metrics = ["Tax Burden", "Interest Burden", "Operating Margin", "Asset Turnover", "Equity Multiplier (Leverage)", "ROE"]
df_dupont = pd.DataFrame({
    "Metric": metrics,
    ticker_a: dupont_a,
    ticker_b: dupont_b
}).set_index("Metric")

st.dataframe(df_dupont.style.format("{:.2f}").highlight_max(axis=1, color='#a8d08d'), use_container_width=True)

# --- 4. DOOMSDAY LIQUIDITY RUNWAY (STRESS TEST) ---
st.divider()
st.subheader("3. 'Doomsday' Liquidity Runway (Shock Simulation)")
st.caption(f"Simulating a {rev_shock}% revenue collapse and a {rate_shock_bps*10000:.0f} bps interest rate spike.")

def calc_runway(d, r_shock, i_shock):
    # Shocked monthly revenue and operational costs
    monthly_rev = (d["Revenue"] * (1 + (r_shock/100))) / 12
    # Assume 85% of revenue represents fixed/variable operating costs in a crisis
    monthly_opex = (d["Revenue"] * 0.85) / 12 
    
    # Shocked debt servicing
    monthly_interest = (d["Interest Exp"] + (d["Total Debt"] * i_shock)) / 12
    
    monthly_burn = monthly_opex + monthly_interest - monthly_rev
    runway_months = d["Cash"] / monthly_burn if monthly_burn > 0 else 999
    return monthly_burn, runway_months

burn_a, runway_a = calc_runway(data_a, rev_shock, rate_shock_bps)
burn_b, runway_b = calc_runway(data_b, rev_shock, rate_shock_bps)

col1, col2 = st.columns(2)
with col1:
    st.metric(f"{ticker_a} Cash Runway", f"{runway_a:.1f} Months", 
              help=f"Monthly Burn Rate: ${burn_a:,.0f}", delta_color="inverse")
with col2:
    st.metric(f"{ticker_b} Cash Runway", f"{runway_b:.1f} Months", 
              help=f"Monthly Burn Rate: ${burn_b:,.0f}", delta_color="inverse")

# Interactive Runway Chart
months = np.arange(0, 25)
cash_a_trend = [max(0, data_a["Cash"] - (burn_a * m)) for m in months]
cash_b_trend = [max(0, data_b["Cash"] - (burn_b * m)) for m in months]

fig_runway = go.Figure()
fig_runway.add_trace(go.Scatter(x=months, y=cash_a_trend, mode='lines', name=ticker_a, line=dict(color='#2563eb', width=3)))
fig_runway.add_trace(go.Scatter(x=months, y=cash_b_trend, mode='lines', name=ticker_b, line=dict(color='#dc2626', width=3)))

fig_runway.add_hline(y=0, line_dash="dash", line_color="black", annotation_text="Insolvency Line")
fig_runway.update_layout(xaxis_title="Months Since Shock", yaxis_title="Remaining Cash Balance", template="plotly_white")
st.plotly_chart(fig_runway, use_container_width=True)