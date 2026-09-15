import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go

st.set_page_config(page_title="Equity Forecaster", layout="wide")
st.title("Macro Shock: Equity & Dividend Forecaster")
st.markdown("Test how economic shifts impact company profits and your future dividends before you invest.")

# --- 1. UNIVERSAL SIDEBAR ---
st.sidebar.header("Stock Selection")
st.sidebar.caption("Use '.JO' for JSE listed stocks (e.g., SHP.JO).")
ticker = st.sidebar.text_input("Enter Ticker (e.g., SHP.JO, AAPL, FSR.JO):", value="SHP.JO").upper()

st.sidebar.divider()
st.sidebar.subheader("Economic Shocks")
rev_shock = st.sidebar.slider("Consumer Demand Growth/Drop (%)", min_value=-30, max_value=20, value=-10, step=1, help="Simulates a drop or spike in top-line sales.")
cost_shock = st.sidebar.slider("Operating Cost Inflation (%)", min_value=0, max_value=30, value=8, step=1, help="Simulates rising fuel, wage, and operational costs.")
rate_shock_bps = st.sidebar.slider("Interest Rate Change (bps)", min_value=0, max_value=400, value=150, step=25, help="100 bps = 1%. Simulates the Central Bank hiking rates.") / 10000
tax_shock = st.sidebar.slider("Corporate Tax Rate Change (%)", min_value=-10, max_value=10, value=0, step=1, help="Simulate government tax hikes or cuts (Absolute %).")
dilution_shock = st.sidebar.slider("Shareholder Dilution (%)", min_value=0, max_value=50, value=0, step=1, help="Simulate the company issuing new shares, shrinking your EPS.")

# --- 2. DATA ENGINE ---
@st.cache_data(ttl=3600)
def fetch_company_data(t_symbol):
    try:
        t = yf.Ticker(t_symbol)
        inc = t.income_stmt
        bs = t.balance_sheet
        info = t.info
        
        # Currency formatting
        currency_code = info.get('financialCurrency', 'USD')
        curr_sym = {'ZAR': 'R', 'USD': '$', 'GBP': '£', 'EUR': '€'}.get(currency_code, currency_code + ' ')
        
        # Pull latest actuals
        rev = inc.loc['Total Revenue'].iloc[0] if 'Total Revenue' in inc.index else 1
        ebit = inc.loc['EBIT'].iloc[0] if 'EBIT' in inc.index else 0
        pretax = inc.loc['Pretax Income'].iloc[0] if 'Pretax Income' in inc.index else 1
        net_inc = inc.loc['Net Income'].iloc[0] if 'Net Income' in inc.index else 1
        interest = abs(inc.loc['Interest Expense'].iloc[0]) if 'Interest Expense' in inc.index else 0
        
        total_debt = bs.loc['Total Debt'].iloc[0] if 'Total Debt' in bs.index else 0
        shares = info.get('sharesOutstanding', 1)
        
        # --- THE JSE MATH FIX ---
        # Yahoo Finance reports JSE (.JO) prices in CENTS, but income statements in RANDS.
        # We divide the raw price by 100 for SA stocks to get the actual Rand price.
        raw_price = info.get('currentPrice', info.get('previousClose', 0))
        current_price = raw_price / 100 if t_symbol.endswith('.JO') else raw_price
        
        # Calculate derived baselines purely from the income statement
        opex = rev - ebit
        tax_rate = (pretax - net_inc) / pretax if pretax > 0 else 0.27 
        base_eps = net_inc / shares if shares else 0
        
        # Use the API's native payout ratio to avoid currency mismatch errors entirely
        payout_ratio = info.get('payoutRatio', 0)
        if payout_ratio is None:
            payout_ratio = 0
            
        base_div_per_share = base_eps * payout_ratio
        # -------------------------
        
        company_name = info.get('shortName', t_symbol)
        
        return {
            "Name": company_name, "Symbol": curr_sym, "Current Price": current_price,
            "Revenue": rev, "OpEx": opex, "Interest": interest, 
            "Total Debt": total_debt, "Tax Rate": tax_rate, "Shares": shares,
            "Base Net Income": net_inc, "Base EPS": base_eps, 
            "Base Div": base_div_per_share, "Payout Ratio": payout_ratio
        }
    except Exception as e:
        return None

with st.spinner(f"Pulling global financial data for {ticker}..."):
    data = fetch_company_data(ticker)

if not data:
    st.error(f"Could not load data for {ticker}. Please verify the ticker symbol.")
    st.stop()

sym = data["Symbol"]

# --- 3. APPLYING THE SHOCKS ---
base_pretax = data["Revenue"] - data["OpEx"] - data["Interest"]
base_tax_paid = base_pretax * data["Tax Rate"] if base_pretax > 0 else 0
base_net_inc = base_pretax - base_tax_paid

shocked_rev = data["Revenue"] * (1 + (rev_shock / 100))
shocked_opex = data["OpEx"] * (1 + (cost_shock / 100))
shocked_interest = data["Interest"] + (data["Total Debt"] * rate_shock_bps)

shocked_pretax = shocked_rev - shocked_opex - shocked_interest
new_tax_rate = max(0, data["Tax Rate"] + (tax_shock / 100))
shocked_tax_paid = shocked_pretax * new_tax_rate if shocked_pretax > 0 else 0
shocked_net_inc = shocked_pretax - shocked_tax_paid

new_shares = data["Shares"] * (1 + (dilution_shock / 100))
shocked_eps = shocked_net_inc / new_shares if new_shares else 0

shocked_div = shocked_eps * data["Payout Ratio"] if shocked_eps > 0 else 0

# --- 4. THE UI HEADER ---
col_title, col_price = st.columns([3, 1])
with col_title:
    st.subheader(f"Analyzing: {data['Name']}")
with col_price:
    st.metric("Live Share Price", f"{sym}{data['Current Price']:,.2f}")

st.caption(f"How your selected economic conditions impact shareholder returns (Displayed in {sym}).")

# --- 5. THE BOTTOM LINE ---
c1, c2 = st.columns(2)
with c1:
    eps_delta = ((shocked_eps - data['Base EPS']) / abs(data['Base EPS'])) * 100 if data['Base EPS'] != 0 else 0
    st.metric("Projected Earnings Per Share (EPS)", f"{sym}{shocked_eps:.2f}", f"{eps_delta:.1f}% vs Baseline", delta_color="normal")

with c2:
    div_delta = ((shocked_div - data['Base Div']) / data['Base Div']) * 100 if data['Base Div'] > 0 else 0
    if data['Base Div'] == 0:
        st.metric("Projected Dividend Per Share", f"{sym}0.00", "Company currently pays no dividend")
    else:
        st.metric("Projected Dividend Per Share", f"{sym}{shocked_div:.2f}", f"{div_delta:.1f}% vs Baseline", delta_color="normal")

# --- 6. THE PROFIT DRAIN WATERFALL ---
st.divider()
st.subheader("Where did the profit go?")
st.caption("A clean breakdown of exactly how inflation, rate hikes, and consumer spending impact the total bottom line.")

delta_rev = shocked_rev - data["Revenue"]
delta_opex = -(shocked_opex - data["OpEx"]) 
delta_int = -(shocked_interest - data["Interest"])
delta_tax = -(shocked_tax_paid - base_tax_paid)

fig = go.Figure(go.Waterfall(
    name="Profit", orientation="v",
    measure=["absolute", "relative", "relative", "relative", "relative", "total"],
    x=["Baseline Net Income", "Demand Impact", "Inflation Impact", "Rate Impact", "Tax Impact", "Projected Net Income"],
    textposition="outside",
    y=[base_net_inc, delta_rev, delta_opex, delta_int, delta_tax, shocked_net_inc],
    connector={"line":{"color":"rgb(63, 63, 63)"}},
    decreasing={"marker":{"color":"#ef4444"}},
    increasing={"marker":{"color":"#22c55e"}},
    totals={"marker":{"color":"#2563eb"}}
))

fig.update_layout(
    title=f"Net Income Breakdown ({sym}) - {data['Name']}",
    showlegend=False,
    template="plotly_white",
    margin=dict(t=40, b=40)
)

st.plotly_chart(fig, use_container_width=True)