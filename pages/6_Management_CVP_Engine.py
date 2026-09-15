import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go

st.set_page_config(page_title="CVP & Break-Even Engine", layout="wide")
st.title("Strategic FP&A: CVP & Break-Even Engine")
st.markdown("Transform static accounting ledgers into forward-looking operational intelligence and break-even analysis.")

# --- 1. DATA INGESTION (DUAL MODE: CSV & EXCEL) ---
st.sidebar.header("Data Ingestion")
uploaded_file = st.sidebar.file_uploader(
    "Upload Income Statement (CSV or Excel)", 
    type=["csv", "xlsx", "xls"], 
    help="Must contain 'Category', 'Classification' (Fixed/Variable/Revenue), and 'Amount' columns."
)

# Fallback Demo Data so the app is never blank
if uploaded_file is None:
    st.sidebar.info("No file uploaded. Running standard 'SA Retailer' Demo Profile.")
    data = {
        "Category": ["Gross Sales", "Cost of Goods Sold (COGS)", "Logistics & Distribution", "Sales Commissions", "Rent & Rates", "Salaries & Wages", "IT & Administration", "Depreciation"],
        "Classification": ["Revenue", "Variable", "Variable", "Variable", "Fixed", "Fixed", "Fixed", "Fixed"],
        "Amount": [5000000, 2200000, 300000, 150000, 450000, 600000, 120000, 80000]
    }
    df = pd.DataFrame(data)
else:
    try:
        # Check the file extension and use the correct Pandas reader
        if uploaded_file.name.endswith('.csv'):
            df = pd.read_csv(uploaded_file)
        else:
            df = pd.read_excel(uploaded_file)
    except Exception as e:
        st.error("Error reading file. Please ensure it is a valid CSV or Excel document.")
        st.stop()

# --- 2. OPERATIONAL BUDGETING SHOCKS ---
st.sidebar.divider()
st.sidebar.subheader("Management Budget Scenarios")
volume_change = st.sidebar.slider("Sales Volume Growth (%)", min_value=-50, max_value=50, value=0, step=5)
price_change = st.sidebar.slider("Product Pricing Power (%)", min_value=-20, max_value=50, value=0, step=2)
vc_inflation = st.sidebar.slider("Variable Cost Inflation (%)", min_value=-10, max_value=50, value=0, step=2, help="e.g., Supplier price hikes or fuel increases.")
fc_adjustment = st.sidebar.slider("Fixed Cost Cuts/Hikes (%)", min_value=-30, max_value=50, value=0, step=5, help="e.g., Layoffs or office expansion.")

# --- 3. AUTO-CLASSIFICATION & MATH ENGINE ---
# Baseline Aggregation
base_revenue = df[df["Classification"] == "Revenue"]["Amount"].sum()
base_vc = df[df["Classification"] == "Variable"]["Amount"].sum()
base_fc = df[df["Classification"] == "Fixed"]["Amount"].sum()

# Scenario Math (The FP&A Magic)
vol_multiplier = 1 + (volume_change / 100.0)
price_multiplier = 1 + (price_change / 100.0)
vc_multiplier = 1 + (vc_inflation / 100.0)
fc_multiplier = 1 + (fc_adjustment / 100.0)

# Stressed Totals
new_revenue = base_revenue * vol_multiplier * price_multiplier
new_vc = base_vc * vol_multiplier * vc_multiplier
new_fc = base_fc * fc_multiplier

new_cm = new_revenue - new_vc
new_cm_ratio = new_cm / new_revenue if new_revenue > 0 else 0
new_ebit = new_cm - new_fc

# Break-Even Logic
break_even_revenue = new_fc / new_cm_ratio if new_cm_ratio > 0 else 0
margin_of_safety = new_revenue - break_even_revenue
mos_pct = (margin_of_safety / new_revenue * 100) if new_revenue > 0 else 0
operating_leverage = new_cm / new_ebit if new_ebit > 0 else 0

# --- 4. UI: THE EXECUTIVE SCORECARD ---
st.subheader("1. Operational Intelligence (Cost-Volume-Profit)")
st.caption("Auto-classified from accounting records into strategic management metrics.")

m1, m2, m3, m4 = st.columns(4)
with m1:
    st.metric("Gross Revenue", f"R {new_revenue:,.0f}", f"{((new_revenue - base_revenue)/base_revenue)*100:.1f}% vs Ledger")
with m2:
    st.metric("Contribution Margin", f"R {new_cm:,.0f}", f"{new_cm_ratio*100:.1f}% Margin")
with m3:
    mos_status = "normal" if mos_pct > 15 else "inverse"
    st.metric("Margin of Safety", f"R {margin_of_safety:,.0f}", f"{mos_pct:.1f}% Buffer", delta_color=mos_status)
with m4:
    st.metric("Degree of Operating Leverage", f"{operating_leverage:.2f}x", help="For every 1% increase in sales, profit will increase by this multiple.")

# --- 5. UI: THE BREAK-EVEN CHART ---
st.divider()
st.subheader("2. The Break-Even Horizon")
st.caption("Visualizing exactly where Total Revenue crosses Total Costs. Operating below the intersection means the business is bleeding cash.")

# Generate data points for the CVP graph
x_sales = np.linspace(0, max(new_revenue, break_even_revenue) * 1.3, 100)
y_fixed_costs = np.full_like(x_sales, new_fc)
y_total_costs = new_fc + (x_sales * (1 - new_cm_ratio))
y_revenue = x_sales

fig_cvp = go.Figure()

# Fixed Costs Line
fig_cvp.add_trace(go.Scatter(x=x_sales, y=y_fixed_costs, mode='lines', name='Fixed Costs', line=dict(color='gray', dash='dash')))
# Total Costs Line
fig_cvp.add_trace(go.Scatter(x=x_sales, y=y_total_costs, mode='lines', name='Total Costs (Fixed + Variable)', line=dict(color='#ef4444', width=3)))
# Total Revenue Line
fig_cvp.add_trace(go.Scatter(x=x_sales, y=y_revenue, mode='lines', name='Total Revenue', line=dict(color='#22c55e', width=3)))

# Mark the Break-Even Point
fig_cvp.add_trace(go.Scatter(
    x=[break_even_revenue], y=[break_even_revenue],
    mode='markers', name='Break-Even Point',
    marker=dict(color='black', size=12, symbol='x')
))

# Current Operation Marker
fig_cvp.add_trace(go.Scatter(
    x=[new_revenue], y=[new_revenue],
    mode='markers', name='Current Budget Run-Rate',
    marker=dict(color='#2563eb', size=10)
))

fig_cvp.update_layout(
    xaxis_title="Sales Volume Generated (R)",
    yaxis_title="Capital (R)",
    template="plotly_white",
    hovermode="x unified",
    margin=dict(t=30, b=30),
    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
)
st.plotly_chart(fig_cvp, use_container_width=True)

# --- 6. UI: THE PROFIT CONVERSION FUNNEL ---
st.divider()
st.subheader("3. Profit Conversion Funnel")
st.caption("Tracking how much of your Gross Revenue survives the operational cost structure to become Net Profit.")

# Determine the color of the final EBIT bar (Green for profit, Red for loss)
ebit_color = "#22c55e" if new_ebit >= 0 else "#ef4444"

fig_funnel = go.Figure(go.Funnel(
    y=["Gross Revenue", "Contribution Margin (After VC)", "Net Operating Profit (After FC)"],
    x=[new_revenue, new_cm, new_ebit],
    textinfo="value+percent initial",
    marker={"color": ["#1e293b", "#3b82f6", ebit_color]}
))

fig_funnel.update_layout(
    template="plotly_white",
    margin=dict(t=40, b=40)
)
st.plotly_chart(fig_funnel, use_container_width=True)

# --- 7. RAW DATA VIEWER ---
with st.expander("View Raw Accounting Ledger Data"):
    st.dataframe(df.style.format({"Amount": "R {:,.0f}"}), use_container_width=True)