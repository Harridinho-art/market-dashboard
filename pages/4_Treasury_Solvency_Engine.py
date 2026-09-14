import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go

st.set_page_config(page_title="Treasury & Solvency War Room", layout="wide")
st.title("Corporate Treasury & Solvency Engine")
st.markdown("Institutional liquidity stress-testing, Altman Z-Score solvency tracking, and debt covenant monitoring.")

# --- 1. WAR ROOM SIDEBAR ---
st.sidebar.header("War Room Parameters")
ticker_a = st.sidebar.text_input("Company A Ticker (e.g., AAL.L, AAPL):", value="AAPL").upper()
ticker_b = st.sidebar.text_input("Company B Ticker (e.g., GLEN.L, MSFT):", value="MSFT").upper()

st.sidebar.divider()
st.sidebar.subheader("Macroeconomic Stress Shocks")
rev_shock = st.sidebar.slider("Revenue Shock (%)", min_value=-100, max_value=20, value=-20, step=5)
rate_shock_bps = st.sidebar.slider("Interest Rate Shock (bps)", min_value=0, max_value=500, value=150, step=25) / 10000
opex_flex = st.sidebar.slider("Management Cost Flexibility (%)", min_value=0, max_value=50, value=20, step=5, 
                               help="Percentage of opex management can rapidly cut during a revenue crisis.")

# --- DATA EXTRACTION ENGINE ---
@st.cache_data(ttl=3600)
def fetch_treasury_data(ticker):
    try:
        t = yf.Ticker(ticker)
        bs = t.balance_sheet
        inc = t.income_stmt
        info = t.info
        
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
        interest_exp = abs(inc.loc['Interest Expense'].iloc[0]) if 'Interest Expense' in inc.index else 1
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

with st.spinner("Executing institutional balance sheet parsing..."):
    data_a = fetch_treasury_data(ticker_a)
    data_b = fetch_treasury_data(ticker_b)

if not data_a or not data_b:
    st.error("Data retrieval failed. Please verify ticker symbols.")
    st.stop()

# --- 2. ALTMAN Z-SCORE (DYNAMIC SCALE) ---
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
st.caption("Z > 2.99: Safe Zone | 1.81 - 2.99: Grey Zone | < 1.81: High Distress Risk.")

max_scale = max(15, int(max(z_a, z_b) * 1.2))

fig_z = go.Figure()
for i, (val, name) in enumerate([(z_a, ticker_a), (z_b, ticker_b)]):
    x_domain = [0, 0.45] if i == 0 else [0.55, 1]
    fig_z.add_trace(go.Indicator(
        mode="number+gauge", value=val, title={'text': name},
        gauge={'axis': {'range': [0, max_scale]},
               'bar': {'color': "#1e293b"},
               'steps': [{'range': [0, 1.81], 'color': "#ef4444"},
                         {'range': [1.81, 2.99], 'color': "#facc15"},
                         {'range': [2.99, max_scale], 'color': "#22c55e"}]},
        domain={'x': x_domain, 'y': [0, 1]}
    ))
fig_z.update_layout(height=280, margin=dict(t=40, b=0, l=10, r=10))
st.plotly_chart(fig_z, use_container_width=True)

# --- 3. DEBT COVENANT & INTEREST COVERAGE RATIO (ICR) ---
st.divider()
st.subheader("2. Debt Covenant & Interest Coverage Stress Test")
st.caption("Evaluating whether operating earnings (EBIT) can comfortably cover debt servicing obligations under rate hikes.")

def calc_icr(d, i_shock):
    shocked_interest = d["Interest Exp"] + (d["Total Debt"] * i_shock)
    icr = d["EBIT"] / shocked_interest if shocked_interest > 0 else 999
    return icr, shocked_interest

icr_a, int_a = calc_icr(data_a, rate_shock_bps)
icr_b, int_b = calc_icr(data_b, rate_shock_bps)

c_col1, c_col2 = st.columns(2)
with c_col1:
    st.metric(f"{ticker_a} Interest Coverage (ICR)", f"{icr_a:.2f}x", 
              delta="Safe (> 3.0x)" if icr_a > 3.0 else "Covenant Breach Risk (< 3.0x)",
              delta_color="normal" if icr_a > 3.0 else "inverse")
with c_col2:
    st.metric(f"{ticker_b} Interest Coverage (ICR)", f"{icr_b:.2f}x", 
              delta="Safe (> 3.0x)" if icr_b > 3.0 else "Covenant Breach Risk (< 3.0x)",
              delta_color="normal" if icr_b > 3.0 else "inverse")

# --- 4. DOOMSDAY LIQUIDITY RUNWAY (FLEXIBLE OPEX) ---
st.divider()
st.subheader("3. 'Doomsday' Liquidity Runway Simulation")
st.caption(f"Simulating a {rev_shock}% revenue shock with management cutting flexible operating costs by {opex_flex}%.")

def calc_runway(d, r_shock, i_shock, opex_reduction):
    shocked_rev = (d["Revenue"] * (1 + (r_shock / 100))) / 12
    base_monthly_opex = (d["Revenue"] * 0.75) / 12 # Estimated baseline opex
    flexible_opex = base_monthly_opex * (1 - (opex_reduction / 100))
    
    shocked_interest = (d["Interest Exp"] + (d["Total Debt"] * i_shock)) / 12
    
    monthly_burn = flexible_opex + shocked_interest - shocked_rev
    runway = d["Cash"] / monthly_burn if monthly_burn > 0 else 999.0
    return monthly_burn, runway

burn_a, runway_a = calc_runway(data_a, rev_shock, rate_shock_bps, opex_flex)
burn_b, runway_b = calc_runway(data_b, rev_shock, rate_shock_bps, opex_flex)

m_col1, m_col2 = st.columns(2)
with m_col1:
    st.metric(f"{ticker_a} Cash Runway", f"{runway_a:.1f} Months", help=f"Net Monthly Burn: ${burn_a:,.0f}")
with m_col2:
    st.metric(f"{ticker_b} Cash Runway", f"{runway_b:.1f} Months", help=f"Net Monthly Burn: ${burn_b:,.0f}")

# Runway Projection Chart
months = np.arange(0, 25)
cash_a_trend = [max(0, data_a["Cash"] - (burn_a * m)) for m in months]
cash_b_trend = [max(0, data_b["Cash"] - (burn_b * m)) for m in months]

fig_runway = go.Figure()
fig_runway.add_trace(go.Scatter(x=months, y=cash_a_trend, mode='lines', name=ticker_a, line=dict(color='#2563eb', width=3)))
fig_runway.add_trace(go.Scatter(x=months, y=cash_b_trend, mode='lines', name=ticker_b, line=dict(color='#dc2626', width=3)))
fig_runway.add_hline(y=0, line_dash="dash", line_color="black", annotation_text="Insolvency Line")
fig_runway.update_layout(xaxis_title="Months Since Crisis Event", yaxis_title="Remaining Cash Reserves ($)", template="plotly_white")
st.plotly_chart(fig_runway, use_container_width=True)

# --- 5. 5-WAY DUPONT DECOMPOSITION ---
st.divider()
st.subheader("4. 5-Way DuPont ROE Decomposition")
st.caption("Dissecting return on equity into operational efficiency, tax burden, interest burden, and financial leverage.")

def calc_dupont(d):
    tax_burden = d["Net Income"] / d["Pretax Income"] if d["Pretax Income"] else 0
    int_burden = d["Pretax Income"] / d["EBIT"] if d["EBIT"] else 0
    op_margin = d["EBIT"] / d["Revenue"] if d["Revenue"] else 0
    asset_turnover = d["Revenue"] / d["Total Assets"] if d["Total Assets"] else 0
    leverage = d["Total Assets"] / d["Total Equity"] if d["Total Equity"] else 0
    roe = tax_burden * int_burden * op_margin * asset_turnover * leverage
    return [tax_burden, int_burden, op_margin, asset_turnover, leverage, roe]

df_dupont = pd.DataFrame({
    "Metric": ["Tax Burden", "Interest Burden", "Operating Margin", "Asset Turnover", "Equity Multiplier", "ROE"],
    ticker_a: calc_dupont(data_a),
    ticker_b: calc_dupont(data_b)
}).set_index("Metric")

st.dataframe(df_dupont.style.format("{:.2f}").highlight_max(axis=1, color='#a8d08d'), use_container_width=True)