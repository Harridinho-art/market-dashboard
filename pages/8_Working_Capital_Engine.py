import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go

# --- 1. PAGE SETUP (NO SIDEBAR) ---
st.set_page_config(page_title="Working Capital Engine", layout="wide", initial_sidebar_state="collapsed")
st.title("Corporate Liquidity: Working Capital & CCC Engine")
st.markdown("Analyze the Cash Conversion Cycle (CCC), detect overtrading risks, and quantify short-term funding requirements.")

# --- 2. MAIN WINDOW CONTROL PANEL ---
st.subheader("1. Operational Control Panel")
st.caption("All operational inputs are centralized here. Adjust the sliders to stress-test working capital policies.")

# The input container directly in the main window
with st.container(border=True):
    col_input, col_sliders1, col_sliders2 = st.columns([1, 1.5, 1.5])
    
    with col_input:
        ticker = st.text_input("Analyze Corporate Ticker (e.g., SHP.JO, TFG.JO, AAPL):", value="SHP.JO").upper()
        st.markdown("*Use local retail or manufacturing giants for best CCC results.*")
        
    with col_sliders1:
        inventory_shock = st.slider("Target Inventory Days (DIO) Change", min_value=-30, max_value=30, value=0, step=1, help="Simulate faster stock turnover (-) or dead stock accumulation (+).")
        receivables_shock = st.slider("Debtors Collection (DSO) Change", min_value=-30, max_value=30, value=0, step=1, help="Simulate stricter credit control (-) or delayed customer payments (+).")
        
    with col_sliders2:
        payables_shock = st.slider("Creditor Terms (DPO) Change", min_value=-30, max_value=30, value=0, step=1, help="Simulate negotiating longer terms to pay suppliers (+) or paying early (-).")
        borrowing_rate = st.number_input("Short-Term Borrowing Rate (%)", min_value=1.0, max_value=25.0, value=11.5, step=0.5, help="Cost of a Revolving Credit Facility (RCF) or Overdraft.")

# --- 3. DATA ENGINE ---
@st.cache_data(ttl=3600)
def fetch_working_capital(t_symbol):
    try:
        t = yf.Ticker(t_symbol)
        bs = t.balance_sheet
        inc = t.income_stmt
        info = t.info
        
        curr_code = info.get('financialCurrency', 'USD')
        sym = {'ZAR': 'R', 'USD': '$', 'GBP': '£', 'EUR': '€'}.get(curr_code, curr_code + ' ')
        
        # Balance Sheet 
        inventory = bs.loc['Inventory'].iloc[0] if 'Inventory' in bs.index else 0
        receivables = bs.loc['Accounts Receivable'].iloc[0] if 'Accounts Receivable' in bs.index else 0
        payables = bs.loc['Accounts Payable'].iloc[0] if 'Accounts Payable' in bs.index else 0
        
        # Income Statement
        revenue = inc.loc['Total Revenue'].iloc[0] if 'Total Revenue' in inc.index else 1
        cogs = abs(inc.loc['Cost Of Revenue'].iloc[0]) if 'Cost Of Revenue' in inc.index else (revenue * 0.6) # Fallback assumption
        
        company_name = info.get('shortName', t_symbol)
        
        # Core Baseline Math
        dio = (inventory / cogs) * 365 if cogs > 0 else 0
        dso = (receivables / revenue) * 365 if revenue > 0 else 0
        dpo = (payables / cogs) * 365 if cogs > 0 else 0
        ccc = dio + dso - dpo
        
        daily_cogs = cogs / 365
        
        return {
            "Name": company_name, "Symbol": sym, 
            "DIO": dio, "DSO": dso, "DPO": dpo, "CCC": ccc,
            "Daily_COGS": daily_cogs, "Revenue": revenue,
            "Inventory": inventory, "Receivables": receivables, "Payables": payables
        }
    except Exception as e:
        return None

with st.spinner("Extracting Working Capital fundamentals..."):
    data = fetch_working_capital(ticker)

if not data:
    st.error(f"Could not load working capital data for {ticker}. The company may not carry standard inventory/receivables.")
    st.stop()

sym = data["Symbol"]

# --- 4. SHOCK CALCULATIONS ---
# Apply the slider adjustments to the baseline metrics
new_dio = max(0, data["DIO"] + inventory_shock)
new_dso = max(0, data["DSO"] + receivables_shock)
new_dpo = max(0, data["DPO"] + payables_shock)

new_ccc = new_dio + new_dso - new_dpo

# The Funding Gap (Textbook Section 11.3.1)
# How much cash is required to fund the days the company is waiting for cash?
base_funding_req = max(0, data["CCC"] * data["Daily_COGS"])
new_funding_req = max(0, new_ccc * data["Daily_COGS"])

funding_delta = new_funding_req - base_funding_req
interest_cost = new_funding_req * (borrowing_rate / 100.0)

# --- 5. EXECUTIVE DASHBOARD ---
st.divider()
st.subheader(f"2. Cash Conversion Cycle (CCC): {data['Name']}")

c1, c2, c3, c4 = st.columns(4)
with c1:
    st.metric("Days Inventory (DIO)", f"{new_dio:.0f} Days", f"{inventory_shock} Days vs Base", delta_color="inverse")
with c2:
    st.metric("Days Sales (DSO)", f"{new_dso:.0f} Days", f"{receivables_shock} Days vs Base", delta_color="inverse")
with c3:
    st.metric("Days Payable (DPO)", f"{new_dpo:.0f} Days", f"{payables_shock} Days vs Base", delta_color="normal") # Higher DPO is better for cash
with c4:
    ccc_delta = new_ccc - data["CCC"]
    st.metric("Net Cash Cycle (CCC)", f"{new_ccc:.0f} Days", f"{ccc_delta:.0f} Days vs Base", delta_color="inverse")

# --- 6. THE LIQUIDITY VISUALIZATION ---
st.divider()
st.subheader("3. The Working Capital Timeline")
st.caption("If the red Total CCC bar is positive, the business experiences a cash gap and requires external funding.")

fig = go.Figure(go.Waterfall(
    name="CCC", orientation="v",
    measure=["relative", "relative", "relative", "total"],
    x=["+ Time Stock Sits (DIO)", "+ Time Clients Owe (DSO)", "- Supplier Credit (DPO)", "Cash Conversion Cycle (CCC)"],
    textposition="outside",
    text=[f"{new_dio:.0f}d", f"{new_dso:.0f}d", f"-{new_dpo:.0f}d", f"{new_ccc:.0f} Days"],
    y=[new_dio, new_dso, -new_dpo, new_ccc],
    connector={"line":{"color":"rgb(63, 63, 63)"}},
    decreasing={"marker":{"color":"#22c55e"}}, # Good (Suppliers acting as free financing)
    increasing={"marker":{"color":"#f59e0b"}}, # Warning (Cash locked in stock/debtors)
    totals={"marker":{"color":"#ef4444" if new_ccc > 0 else "#2563eb"}} 
))

fig.update_layout(
    title="Lifecycle of a Rand: From Purchasing to Collection",
    showlegend=False,
    template="plotly_white",
    yaxis_title="Days",
    margin=dict(t=40, b=40)
)
st.plotly_chart(fig, use_container_width=True)

# --- 7. OVERTRADING & FUNDING REQUIREMENTS (TEXTBOOK CH 11.2 & 11.3.1) ---
st.divider()
st.subheader("4. Liquidity & Overtrading Risk (Funding Requirements)")

col_fund1, col_fund2 = st.columns(2)

with col_fund1:
    st.info("**Capital Funding Requirement**")
    st.markdown(f"""
    To sustain operations with a Cash Conversion Cycle of **{new_ccc:.0f} days**, the company requires a short-term liquidity bridge:
    
    * **Required Facility:** `{sym}{new_funding_req:,.0f}`
    * **Annual Interest Cost:** `{sym}{interest_cost:,.0f}`
    
    *If sales volume spikes unexpectedly without securing this facility, the company faces severe **Overtrading** risk (insolvency despite profitability).*
    """)

with col_fund2:
    if new_ccc > data["CCC"]:
        st.error("**Risk Alert: Widening Cash Gap**")
        st.markdown(f"Your adjusted policies have increased the cash gap by **{ccc_delta:.0f} days**. You now require an additional **{sym}{funding_delta:,.0f}** in short-term working capital compared to the baseline.")
    elif new_ccc < 0:
        st.success("**Operational Excellence: Negative CCC**")
        st.markdown(f"The company is operating with a negative cycle. Suppliers are completely funding the business's inventory and sales. Zero short-term working capital facilities are required.")
    else:
        st.success("**Optimization Achieved**")
        st.markdown(f"Your adjusted policies have shrunk the cash gap by **{abs(ccc_delta):.0f} days**, freeing up **{sym}{abs(funding_delta):,.0f}** in trapped cash. This reduces reliance on expensive short-term debt.")