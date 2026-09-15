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
st.caption("Upload your own working capital ledger, or search a live corporate ticker. Adjust the sliders to stress-test policies.")

with st.container(border=True):
    col_upload, col_ticker, col_sliders = st.columns([1, 1, 1.5])
    
    with col_upload:
        st.markdown("**Option A: Custom Upload**")
        uploaded_file = st.file_uploader("Upload Ledger (CSV/Excel)", type=["csv", "xlsx", "xls"], help="Requires columns: 'Metric' and 'Amount' (Inventory, Receivables, Payables, Revenue, COGS)")
        
    with col_ticker:
        st.markdown("**Option B: Live Market Data**")
        ticker = st.text_input("Analyze Corporate Ticker:", value="SHP.JO").upper()
        st.caption("*Leave upload blank to use live ticker.*")
        
    with col_sliders:
        st.markdown("**Stress-Test Parameters**")
        c1, c2 = st.columns(2)
        with c1:
            inventory_shock = st.slider("Inventory Days (DIO) Change", -30, 30, 0, 1)
            receivables_shock = st.slider("Debtors (DSO) Change", -30, 30, 0, 1)
        with c2:
            payables_shock = st.slider("Creditor (DPO) Change", -30, 30, 0, 1)
            borrowing_rate = st.number_input("Short-Term Borrowing Rate (%)", 1.0, 25.0, 11.5, 0.5)

# --- 3. DATA ENGINE (DUAL MODE) ---
@st.cache_data(ttl=3600)
def process_working_capital(file, t_symbol):
    try:
        # MODE A: Custom File Upload
        if file is not None:
            if file.name.endswith('.csv'):
                df_raw = pd.read_csv(file)
            else:
                df_raw = pd.read_excel(file)
            
            # Map uploaded data (assuming 'Metric' and 'Amount' columns)
            val_map = dict(zip(df_raw['Metric'].str.lower(), df_raw['Amount']))
            
            inventory = val_map.get('inventory', 0)
            receivables = val_map.get('accounts receivable', val_map.get('receivables', 0))
            payables = val_map.get('accounts payable', val_map.get('payables', 0))
            revenue = val_map.get('revenue', val_map.get('sales', 1))
            cogs = val_map.get('cost of goods sold', val_map.get('cogs', revenue * 0.6))
            
            company_name = "Custom Uploaded Profile"
            sym = "R "
            
        # MODE B: Live Ticker
        else:
            t = yf.Ticker(t_symbol)
            bs = t.balance_sheet
            inc = t.income_stmt
            info = t.info
            
            curr_code = info.get('financialCurrency', 'USD')
            sym = {'ZAR': 'R ', 'USD': '$', 'GBP': '£', 'EUR': '€'}.get(curr_code, curr_code + ' ')
            
            inventory = bs.loc['Inventory'].iloc[0] if 'Inventory' in bs.index else 0
            receivables = bs.loc['Accounts Receivable'].iloc[0] if 'Accounts Receivable' in bs.index else 0
            payables = bs.loc['Accounts Payable'].iloc[0] if 'Accounts Payable' in bs.index else 0
            
            revenue = inc.loc['Total Revenue'].iloc[0] if 'Total Revenue' in inc.index else 1
            cogs = abs(inc.loc['Cost Of Revenue'].iloc[0]) if 'Cost Of Revenue' in inc.index else (revenue * 0.6)
            
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
            "Daily_COGS": daily_cogs
        }
    except Exception as e:
        return None

with st.spinner("Processing Working Capital fundamentals..."):
    data = process_working_capital(uploaded_file, ticker)

if not data:
    st.error("Could not load working capital data. Check the ticker or ensure your uploaded file has 'Metric' and 'Amount' columns.")
    st.stop()

sym = data["Symbol"]

# --- 4. SHOCK CALCULATIONS ---
new_dio = max(0, data["DIO"] + inventory_shock)
new_dso = max(0, data["DSO"] + receivables_shock)
new_dpo = max(0, data["DPO"] + payables_shock)
new_ccc = new_dio + new_dso - new_dpo

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
    st.metric("Days Payable (DPO)", f"{new_dpo:.0f} Days", f"{payables_shock} Days vs Base", delta_color="normal") 
with c4:
    ccc_delta = new_ccc - data["CCC"]
    st.metric("Net Cash Cycle (CCC)", f"{new_ccc:.0f} Days", f"{ccc_delta:.0f} Days vs Base", delta_color="inverse")

# --- 6. THE NEW VISUALIZATION: CCC GANTT TIMELINE ---
st.divider()
st.subheader("3. The Working Capital Timeline (Days)")
st.caption("A calendar view of cash flow. The red bar represents the physical days the business must survive without cash.")

fig = go.Figure()

# 1. Payables (How long we hold onto our cash)
fig.add_trace(go.Bar(
    y=['0. Payables (Cash Retained)'],
    x=[new_dpo],
    base=0,
    orientation='h',
    name='Days Payable (DPO)',
    marker_color='#22c55e', # Green (Good)
    text=[f"{new_dpo:.0f} Days"],
    textposition='inside'
))

# 2. Inventory (How long stock sits on the shelf)
fig.add_trace(go.Bar(
    y=['1. Inventory (Cash Tied Up)'],
    x=[new_dio],
    base=0,
    orientation='h',
    name='Days Inventory (DIO)',
    marker_color='#3b82f6', # Blue
    text=[f"{new_dio:.0f} Days"],
    textposition='inside'
))

# 3. Receivables (How long customers take to pay)
fig.add_trace(go.Bar(
    y=['2. Receivables (Waiting for Cash)'],
    x=[new_dso],
    base=new_dio, # Starts exactly when Inventory ends
    orientation='h',
    name='Days Sales (DSO)',
    marker_color='#f59e0b', # Orange
    text=[f"{new_dso:.0f} Days"],
    textposition='inside'
))

# 4. The Cash Gap (The CCC)
if new_ccc > 0:
    fig.add_trace(go.Bar(
        y=['3. The Cash Gap (CCC)'],
        x=[new_ccc],
        base=new_dpo, # Starts exactly when we have to pay our suppliers
        orientation='h',
        name='Cash Gap (Funding Required)',
        marker_color='#ef4444', # Red (Danger)
        text=[f"Gap: {new_ccc:.0f} Days"],
        textposition='inside'
    ))

fig.update_layout(
    barmode='overlay',
    template='plotly_white',
    xaxis_title="Timeline (Days from Stock Arrival)",
    height=400,
    margin=dict(t=30, b=30),
    showlegend=False
)
st.plotly_chart(fig, use_container_width=True)

# --- 7. OVERTRADING & FUNDING REQUIREMENTS ---
st.divider()
st.subheader("4. Liquidity & Overtrading Risk (Funding Requirements)")

col_fund1, col_fund2 = st.columns(2)

with col_fund1:
    st.info("**Capital Funding Requirement**")
    st.markdown(f"""
    To sustain operations with a Cash Conversion Cycle of **{new_ccc:.0f} days**, the company requires a short-term liquidity bridge:
    
    * **Required Facility:** `{sym}{new_funding_req:,.0f}`
    * **Annual Interest Cost:** `{sym}{interest_cost:,.0f}`
    
    *If sales volume spikes unexpectedly without securing this facility, the company faces severe **Overtrading** risk.*
    """)

with col_fund2:
    if new_ccc > data["CCC"]:
        st.error("**Risk Alert: Widening Cash Gap**")
        st.markdown(f"Your adjusted policies have increased the cash gap by **{ccc_delta:.0f} days**. You now require an additional **{sym}{funding_delta:,.0f}** in short-term working capital compared to the baseline.")
    elif new_ccc <= 0:
        st.success("**Operational Excellence: Negative CCC**")
        st.markdown(f"The company is operating with a negative cycle. Suppliers are completely funding the business's inventory and sales. Zero short-term working capital facilities are required.")
    else:
        st.success("**Optimization Achieved**")
        st.markdown(f"Your adjusted policies have shrunk the cash gap by **{abs(ccc_delta):.0f} days**, freeing up **{sym}{abs(funding_delta):,.0f}** in trapped cash. This reduces reliance on expensive short-term debt.")