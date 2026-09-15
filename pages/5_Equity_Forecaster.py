import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go

st.set_page_config(page_title="JSE Equity Forecaster", layout="wide")
st.title("JSE Equity & Dividend Forecaster")
st.markdown("Test how South African economic shifts (inflation, SARB rate hikes, consumer demand) impact local stock profits and your future dividends before you invest.")

# --- 1. LOCALIZED SIDEBAR ---
st.sidebar.header("JSE Stock Selection")
st.sidebar.caption("Use '.JO' for Johannesburg Stock Exchange tickers.")
ticker = st.sidebar.text_input("Enter JSE Ticker (e.g., SHP.JO, FSR.JO, SBK.JO, MTN.JO):", value="SHP.JO").upper()

st.sidebar.divider()
st.sidebar.subheader("SA Economic Shocks")
rev_shock = st.sidebar.slider("Consumer Demand Growth/Drop (%)", min_value=-30, max_value=20, value=-10, step=1, help="Simulates a drop in sales due to consumer pressure.")
cost_shock = st.sidebar.slider("Operating Cost Inflation (%)", min_value=0, max_value=30, value=8, step=1, help="Simulates rising fuel, wage, and operational costs.")
rate_shock_bps = st.sidebar.slider("SARB Interest Rate Change (bps)", min_value=0, max_value=400, value=150, step=25, help="100 bps = 1%. Simulates the Reserve Bank hiking rates.") / 10000

# --- 2. DATA ENGINE ---
@st.cache_data(ttl=3600)
def fetch_company_data(t_symbol):
    try:
        t = yf.Ticker(t_symbol)
        inc = t.income_stmt
        bs = t.balance_sheet
        info = t.info
        
        # Pull latest actuals (using ZAR)
        rev = inc.loc['Total Revenue'].iloc[0] if 'Total Revenue' in inc.index else 1
        ebit = inc.loc['EBIT'].iloc[0] if 'EBIT' in inc.index else 0
        pretax = inc.loc['Pretax Income'].iloc[0] if 'Pretax Income' in inc.index else 1
        net_inc = inc.loc['Net Income'].iloc[0] if 'Net Income' in inc.index else 1
        interest = abs(inc.loc['Interest Expense'].iloc[0]) if 'Interest Expense' in inc.index else 0
        
        total_debt = bs.loc['Total Debt'].iloc[0] if 'Total Debt' in bs.index else 0
        shares = info.get('sharesOutstanding', 1)
        
        # Calculate derived baselines
        opex = rev - ebit
        tax_rate = (pretax - net_inc) / pretax if pretax > 0 else 0.27 # Default SA corporate tax rate approx
        base_eps = net_inc / shares if shares else 0
        
        # Dividend logic
        div_yield = info.get('dividendYield', 0)
        current_price = info.get('currentPrice', info.get('previousClose', 1))
        base_div_per_share = div_yield * current_price if div_yield else 0
        payout_ratio = base_div_per_share / base_eps if base_eps > 0 else 0
        payout_ratio = min(max(payout_ratio, 0), 1) 
        
        company_name = info.get('shortName', t_symbol)
        
        return {
            "Name": company_name, "Revenue": rev, "OpEx": opex, "Interest": interest, 
            "Total Debt": total_debt, "Tax Rate": tax_rate, "Shares": shares,
            "Base Net Income": net_inc, "Base EPS": base_eps, 
            "Base Div": base_div_per_share, "Payout Ratio": payout_ratio
        }
    except Exception as e:
        return None

with st.spinner(f"Pulling JSE financial data for {ticker}..."):
    data = fetch_company_data(ticker)

if not data:
    st.error(f"Could not load data for {ticker}. Ensure you include the '.JO' suffix for South African stocks.")
    st.stop()

st.subheader(f"Analyzing: {data['Name']}")

# --- 3. APPLYING THE SHOCKS ---
shocked_rev = data["Revenue"] * (1 + (rev_shock / 100))
shocked_opex = data["OpEx"] * (1 + (cost_shock / 100))
shocked_interest = data["Interest"] + (data["Total Debt"] * rate_shock_bps)

shocked_pretax = shocked_rev - shocked_opex - shocked_interest
shocked_net_inc = shocked_pretax * (1 - data["Tax Rate"])
shocked_eps = shocked_net_inc / data["Shares"]

shocked_div = shocked_eps * data["Payout Ratio"] if shocked_eps > 0 else 0

# --- 4. THE BOTTOM LINE (UI) ---
st.caption("How your selected economic conditions impact shareholder returns (Displayed in ZAR).")

c1, c2 = st.columns(2)

with c1:
    eps_delta = ((shocked_eps - data['Base EPS']) / abs(data['Base EPS'])) * 100 if data['Base EPS'] != 0 else 0
    st.metric("Projected Earnings Per Share (EPS)", f"R {shocked_eps:.2f}", f"{eps_delta:.1f}% vs Current Baseline", delta_color="normal")

with c2:
    div_delta = ((shocked_div - data['Base Div']) / data['Base Div']) * 100 if data['Base Div'] > 0 else 0
    if data['Base Div'] == 0:
        st.metric("Projected Dividend Per Share", "R 0.00", "Company currently pays no dividend")
    else:
        st.metric("Projected Dividend Per Share", f"R {shocked_div:.2f}", f"{div_delta:.1f}% vs Current Baseline", delta_color="normal")

# --- 5. THE PROFIT DRAIN WATERFALL ---
st.divider()
st.subheader("Where did the profit go?")
st.caption("A clean breakdown of exactly how inflation, rate hikes, and consumer spending impact the company's bottom line.")

rev_impact = shocked_rev - data["Revenue"]
opex_impact = -(shocked_opex - data["OpEx"]) 
int_impact = -(shocked_interest - data["Interest"])
tax_impact = (shocked_net_inc - data["Base Net Income"]) - (rev_impact + opex_impact + int_impact)

fig = go.Figure(go.Waterfall(
    name="Profit", orientation="v",
    measure=["absolute", "relative", "relative", "relative", "relative", "total"],
    x=["Current Net Income", "Consumer Demand Impact", "Inflation Impact", "SARB Rate Impact", "Tax Adjustment", "Projected Net Income"],
    textposition="outside",
    y=[data["Base Net Income"], rev_impact, opex_impact, int_impact, tax_impact, shocked_net_inc],
    connector={"line":{"color":"rgb(63, 63, 63)"}},
    decreasing={"marker":{"color":"#ef4444"}},
    increasing={"marker":{"color":"#22c55e"}},
    totals={"marker":{"color":"#2563eb"}}
))

fig.update_layout(
    title=f"Net Income Breakdown (ZAR) - {data['Name']}",
    showlegend=False,
    template="plotly_white",
    margin=dict(t=40, b=40)
)

st.plotly_chart(fig, use_container_width=True)