import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from datetime import datetime

st.set_page_config(page_title="Debtors & Credit Control", layout="wide")
st.title("Credit Risk: Debtors Age Analysis & ECL")
st.markdown("Automated Accounts Receivable aging, cash trapping alerts, and IFRS 9 Expected Credit Loss (ECL) provisioning.")

# --- 1. DATA INGESTION (DUAL MODE) ---
st.sidebar.header("Ledger Ingestion")
uploaded_file = st.sidebar.file_uploader(
    "Upload Debtors Ledger (CSV or Excel)", 
    type=["csv", "xlsx", "xls"], 
    help="Must contain 'Customer', 'Invoice_Date' (YYYY-MM-DD), and 'Amount'."
)

# Fallback Demo Data ensuring dynamic dates so buckets always work
if uploaded_file is None:
    st.sidebar.info("No file uploaded. Running standard 'SA Wholesaler' Demo Profile.")
    today = pd.to_datetime('today')
    data = {
        "Customer": ["Highveld Traders", "Zungu Logistics", "eMalahleni Retail Hub", "KZN Exporters", "Cape Wholesalers", "Limpopo Mining Supplies", "Soweto Spaza Network"],
        "Invoice_Date": [
            today - pd.Timedelta(days=12),   # Current
            today - pd.Timedelta(days=45),   # 31-60
            today - pd.Timedelta(days=75),   # 61-90
            today - pd.Timedelta(days=105),  # 91-120
            today - pd.Timedelta(days=150),  # 120+
            today - pd.Timedelta(days=20),   # Current
            today - pd.Timedelta(days=85)    # 61-90
        ],
        "Amount": [125000, 45000, 78000, 112000, 54000, 210000, 34000]
    }
    df = pd.DataFrame(data)
else:
    try:
        if uploaded_file.name.endswith('.csv'):
            df = pd.read_csv(uploaded_file)
        else:
            df = pd.read_excel(uploaded_file)
    except Exception as e:
        st.error("Error reading file. Ensure it is a valid CSV or Excel document.")
        st.stop()

# Ensure dates are parsed correctly
df['Invoice_Date'] = pd.to_datetime(df['Invoice_Date'])
df['Days_Outstanding'] = (pd.to_datetime('today') - df['Invoice_Date']).dt.days

# --- 2. THE AGING ENGINE ---
def categorize_aging(days):
    if days <= 30:
        return '1. Current (0-30)'
    elif days <= 60:
        return '2. 31-60 Days'
    elif days <= 90:
        return '3. 61-90 Days'
    elif days <= 120:
        return '4. 91-120 Days'
    else:
        return '5. 120+ Days (High Risk)'

df['Aging_Bucket'] = df['Days_Outstanding'].apply(categorize_aging)

# --- 3. IFRS 9 ECL PROVISIONING SHOCKS ---
st.sidebar.divider()
st.sidebar.subheader("Bad Debt Provisioning (ECL)")
st.sidebar.caption("Set the Expected Credit Loss % for overdue buckets.")

prov_60 = st.sidebar.slider("31-60 Days Risk (%)", 0, 100, 5, step=1)
prov_90 = st.sidebar.slider("61-90 Days Risk (%)", 0, 100, 15, step=5)
prov_120 = st.sidebar.slider("91-120 Days Risk (%)", 0, 100, 50, step=5)
prov_120_plus = st.sidebar.slider("120+ Days Risk (%)", 0, 100, 100, step=5, help="Usually written off entirely.")

# Apply Provision Logic
def calculate_provision(row):
    bucket = row['Aging_Bucket']
    amt = row['Amount']
    if bucket == '2. 31-60 Days': return amt * (prov_60 / 100.0)
    elif bucket == '3. 61-90 Days': return amt * (prov_90 / 100.0)
    elif bucket == '4. 91-120 Days': return amt * (prov_120 / 100.0)
    elif bucket == '5. 120+ Days (High Risk)': return amt * (prov_120_plus / 100.0)
    else: return 0

df['ECL_Provision'] = df.apply(calculate_provision, axis=1)
df['Net_Realizable_Value'] = df['Amount'] - df['ECL_Provision']

# --- 4. CORE METRICS ---
total_book = df['Amount'].sum()
total_provision = df['ECL_Provision'].sum()
net_book = df['Net_Realizable_Value'].sum()

# Cash trapped beyond 60 days
trapped_cash_df = df[df['Days_Outstanding'] > 60]
trapped_cash = trapped_cash_df['Amount'].sum()
trapped_pct = (trapped_cash / total_book) * 100 if total_book > 0 else 0

st.subheader("1. Debtors Book Health Profile")
c1, c2, c3, c4 = st.columns(4)
with c1:
    st.metric("Gross Accounts Receivable", f"R {total_book:,.0f}")
with c2:
    st.metric("Total Bad Debt Provision", f"R {total_provision:,.0f}", f"{(total_provision/total_book)*100:.1f}% of Book", delta_color="inverse")
with c3:
    st.metric("Net Realizable Value", f"R {net_book:,.0f}")
with c4:
    trap_status = "normal" if trapped_pct < 20 else "inverse"
    st.metric("Severe Capital Trapped (>60 Days)", f"R {trapped_cash:,.0f}", f"{trapped_pct:.1f}% of Total Book", delta_color=trap_status)

# --- 5. VISUALIZING THE AGE ANALYSIS ---
st.divider()
st.subheader("2. Accounts Receivable Age Analysis")
st.caption("A pure credit control view of capital distribution across overdue timelines.")

aging_summary = df.groupby('Aging_Bucket')['Amount'].sum().reset_index()

fig_aging = go.Figure(data=[
    go.Bar(
        x=aging_summary['Aging_Bucket'],
        y=aging_summary['Amount'],
        marker_color=['#22c55e', '#eab308', '#f97316', '#ef4444', '#7f1d1d'],
        text=aging_summary['Amount'].apply(lambda x: f"R {x:,.0f}"),
        textposition='auto'
    )
])

fig_aging.update_layout(
    xaxis_title="Aging Buckets",
    yaxis_title="Outstanding Capital (R)",
    template="plotly_white",
    margin=dict(t=20, b=20)
)
st.plotly_chart(fig_aging, use_container_width=True)

# --- 6. THE CREDIT CONTROL LEDGER ---
st.divider()
st.subheader("3. Individual Debtors Credit Ledger")
st.caption("Actionable list for the credit control team showing exact provisions per client.")

display_df = df[['Customer', 'Invoice_Date', 'Days_Outstanding', 'Aging_Bucket', 'Amount', 'ECL_Provision', 'Net_Realizable_Value']].copy()
display_df['Invoice_Date'] = display_df['Invoice_Date'].dt.strftime('%Y-%m-%d')

st.dataframe(
    display_df.style.format({
        "Amount": "R {:,.0f}",
        "ECL_Provision": "R {:,.0f}",
        "Net_Realizable_Value": "R {:,.0f}"
    }), 
    use_container_width=True
)