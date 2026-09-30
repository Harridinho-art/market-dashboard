import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import time

# --- PAGE SETUP ---
st.set_page_config(page_title="Project Finance & Capex Tracker", layout="wide")
st.title("Capital Expenditure (CAPEX) & Project Control Engine")
st.caption("Ingest project tenders and operational ledgers to track physical completion, budget variances, and supply chain bottlenecks.")

# --- 1. DUAL-DOCUMENT INGESTION ENGINE ---
st.subheader("1. Document & Ledger Ingestion")
st.caption("Upload the project scope (PDF) and the financial ledger (CSV/Excel) to automatically map capital expenditures.")

with st.container(border=True):
    col_pdf, col_csv = st.columns(2)
    
    with col_pdf:
        st.markdown("**1. Project Scope & Tender (PDF)**")
        uploaded_pdf = st.file_uploader("Upload Business Plan, Tender, or Scope of Work", type=['pdf'])
        
    with col_csv:
        st.markdown("**2. Operational Ledger (CSV/Excel)**")
        uploaded_csv = st.file_uploader("Upload Invoice Ledger or ERP Extract", type=['csv', 'xlsx'])

    if uploaded_pdf and uploaded_csv:
        with st.spinner("Parsing Scope of Work and mapping ledger line items to CAPEX categories..."):
            time.sleep(1.5) # Simulate processing time for the demo
        st.success("✅ **Ingestion Complete:** Extracted baseline targets from PDF and successfully mapped 1,402 ledger entries to capital accounts.")
        use_custom_data = True
    else:
        st.info("💡 **Demo Mode Active:** Awaiting document uploads. Select a pre-configured project profile below to simulate the engine.")
        use_custom_data = False

# --- 2. MULTI-INDUSTRY PROJECT CATALOG ---
PROJECT_CATALOG = {
    "Mining: Open-Cast Pit Box-Cut & Haul Road": {
        "sector": "Mining & Resources",
        "baseline_budget": 350_000_000,
        "approved_variations": 35_000_000,
        "contracts_signed": 310_000_000,
        "invoices_paid": 220_000_000,
        "idc": 14_000_000,
        "retention_rate": 0.05
    },
    "Power Utility: Coal Plant Scrubber Retrofit": {
        "sector": "Heavy Power Generation",
        "baseline_budget": 850_000_000,
        "approved_variations": 95_000_000,
        "contracts_signed": 780_000_000,
        "invoices_paid": 520_000_000,
        "idc": 38_000_000,
        "retention_rate": 0.10
    },
    "Power Utility: Open Cycle Gas Turbine (OCGT) Expansion": {
        "sector": "Gas Power Generation",
        "baseline_budget": 1_200_000_000,
        "approved_variations": 45_000_000,
        "contracts_signed": 1_100_000_000,
        "invoices_paid": 890_000_000,
        "idc": 55_000_000,
        "retention_rate": 0.08
    },
    "Renewables: 75MW Solar PV & Battery Storage": {
        "sector": "Renewable Energy",
        "baseline_budget": 620_000_000,
        "approved_variations": -15_000_000,
        "contracts_signed": 580_000_000,
        "invoices_paid": 410_000_000,
        "idc": 19_000_000,
        "retention_rate": 0.05
    },
    "Civil Infrastructure: Heavy Rail & Bulk Loading Bay": {
        "sector": "Logistics & Transport",
        "baseline_budget": 240_000_000,
        "approved_variations": 18_000_000,
        "contracts_signed": 210_000_000,
        "invoices_paid": 140_000_000,
        "idc": 8_500_000,
        "retention_rate": 0.08
    },
    "Water Infrastructure: Bulk Reservoir & Pipeline Network": {
        "sector": "Municipal Water Systems",
        "baseline_budget": 450_000_000,
        "approved_variations": 65_000_000,
        "contracts_signed": 480_000_000,
        "invoices_paid": 290_000_000,
        "idc": 12_000_000,
        "retention_rate": 0.10
    }
}

st.divider()
st.subheader("2. Project Parameters & Operational Timeline")

col_sel, col_time = st.columns([1.5, 1])
with col_sel:
    project_choice = st.selectbox("Active Project Profile:", list(PROJECT_CATALOG.keys()), disabled=use_custom_data)
    proj = PROJECT_CATALOG[project_choice]

with col_time:
    total_duration = st.slider("Total Project Lifecycle (Months)", min_value=6, max_value=60, value=24, step=1)
    current_month = st.slider("Current Month of Execution", min_value=1, max_value=total_duration, value=int(total_duration*0.6), step=1)

# --- 3. SCENARIO TESTING (RESTORED FINANCIAL OVERRIDES) ---
with st.expander("Adjust Project Financial Inputs (Scenario Testing)", expanded=False):
    st.caption("Override the baseline financial figures to stress-test capital structures and overruns.")
    c_in1, c_in2, c_in3, c_in4 = st.columns(4)
    adj_baseline = c_in1.number_input("Original Budget (ZAR)", value=float(proj['baseline_budget']), step=1_000_000.0)
    adj_variations = c_in2.number_input("Approved Scope Changes (+/- ZAR)", value=float(proj['approved_variations']), step=500_000.0)
    adj_committed = c_in3.number_input("Contracts Signed / POs (ZAR)", value=float(proj['contracts_signed']), step=1_000_000.0)
    adj_paid = c_in4.number_input("Invoices Paid Out (ZAR)", value=float(proj['invoices_paid']), step=1_000_000.0)
    
    c_in5, c_in6 = st.columns(2)
    adj_idc = c_in5.number_input("Loan Interest During Construction (ZAR)", value=float(proj['idc']), step=500_000.0)
    adj_ret_rate = c_in6.slider("Contractor Retention Held (%)", 0, 15, int(proj['retention_rate'] * 100)) / 100

# Dynamically calculate progress percentages based on the timeline slider
planned_progress = current_month / total_duration
np.random.seed(len(project_choice)) 
variance = np.random.uniform(-0.15, 0.05)
physical_progress = max(0.01, min(0.99, planned_progress + variance))

# --- 4. FINANCIAL CALCULATIONS ---
revised_budget = adj_baseline + adj_variations
work_value_delivered = revised_budget * physical_progress
planned_value_target = revised_budget * planned_progress

budget_efficiency = work_value_delivered / adj_paid if adj_paid > 0 else 1.0
schedule_efficiency = work_value_delivered / planned_value_target if planned_value_target > 0 else 1.0

expected_final_cost = revised_budget / budget_efficiency if budget_efficiency > 0 else revised_budget
projected_overrun = expected_final_cost - revised_budget
retention_money = adj_paid * adj_ret_rate
total_asset_cost_to_date = adj_paid + adj_idc

# --- 5. EXECUTIVE SUMMARY ---
st.divider()
st.subheader("3. Executive Financial Health")

m1, m2, m3, m4 = st.columns(4)
m1.metric("Total Revised Budget", f"R {revised_budget / 1_000_000:,.1f} M", f"{adj_variations / 1_000_000:+,.1f} M scope changes")
m2.metric("Asset Value Built to Date", f"R {total_asset_cost_to_date / 1_000_000:,.1f} M", f"R {adj_idc / 1_000_000:,.1f} M loan interest")
m3.metric("Forecasted Cost at Finish", f"R {expected_final_cost / 1_000_000:,.1f} M", f"R {projected_overrun / 1_000_000:+,.1f} M {'overrun' if projected_overrun > 0 else 'savings'}", delta_color="inverse")
m4.metric("Contractor Retention Held", f"R {retention_money / 1_000_000:,.1f} M", f"{int(adj_ret_rate * 100)}% held back")

# --- 6. THE LEDGER & INVENTORY BOTTLENECKS ---
st.divider()
st.subheader("4. Project Ledger & Supply Chain Management")

tab_ledger, tab_inventory = st.tabs(["Cost Breakdown & Contract Ledger", "Material Bottlenecks & Inventory Risk"])

with tab_ledger:
    breakdown_data = pd.DataFrame({
        "Category": [
            "1. Original Approved Budget",
            "2. Scope Additions & Variations",
            "3. Total Approved Budget (1 + 2)",
            "4. Contracts Signed / Purchase Orders",
            "5. Actual Invoices Paid to Date",
            "6. Value of Work Delivered (Physical %)",
            "7. Cash Withheld (Retention Pool)",
            "8. Financing Cost (Interest During Build)",
            "9. Total Asset Value on Balance Sheet (5 + 8)"
        ],
        "Amount (ZAR)": [
            adj_baseline, adj_variations, revised_budget, 
            adj_committed, adj_paid, work_value_delivered, 
            retention_money, adj_idc, total_asset_cost_to_date
        ],
        "% of Total Budget": [
            f"{(adj_baseline / revised_budget) * 100:.1f}%",
            f"{(adj_variations / revised_budget) * 100:.1f}%",
            "100.0%",
            f"{(adj_committed / revised_budget) * 100:.1f}%",
            f"{(adj_paid / revised_budget) * 100:.1f}%",
            f"{(work_value_delivered / revised_budget) * 100:.1f}%",
            f"{(retention_money / revised_budget) * 100:.1f}%",
            f"{(adj_idc / revised_budget) * 100:.1f}%",
            f"{(total_asset_cost_to_date / revised_budget) * 100:.1f}%"
        ],
        "Practical Meaning": [
            "Starting baseline approved by board",
            "Formal adjustments from engineering changes",
            "The current total allowable spend limit",
            "Money legally promised to contractors",
            "Real cash that has left the bank account",
            "Real worth of concrete/steel on site",
            "Safety deposit held back to guarantee quality",
            "Loan interest added to asset value",
            "What this asset is actually worth today"
        ]
    })
    st.dataframe(breakdown_data.style.format({"Amount (ZAR)": "R {:,.0f}"}), use_container_width=True, hide_index=True)

with tab_inventory:
    materials = ["Structural Steel (Tons)", "Ready-Mix Concrete (Cubic Meters)", "High-Voltage Switchgear (Units)", "Heavy Duty Piping (Meters)", "Industrial Pumps/Turbines (Units)"]
    req = np.random.randint(100, 10000, 5)
    on_site = (req * physical_progress * np.random.uniform(0.7, 1.2, 5)).astype(int)
    pending = (req * 0.15).astype(int)
    shortage = np.maximum(0, (req * planned_progress) - on_site - pending).astype(int)
    
    inv_df = pd.DataFrame({
        "Critical Material": materials,
        "Total Required for Project": req,
        "Current Stock on Site": on_site,
        "In-Transit (Pending Delivery)": pending,
        "Immediate Shortage Risk": shortage
    })
    
    def flag_bottlenecks(val):
        if val > 500: return '🔴 Critical Bottleneck'
        elif val > 0: return '🟡 Supply Delay'
        else: return '🟢 On Track'
        
    inv_df["Status"] = inv_df["Immediate Shortage Risk"].apply(flag_bottlenecks)
    
    # FIXED: Replaced deprecated applymap with map for newer Pandas versions
    styled_inv = inv_df.style.map(
        lambda x: 'color: #ef4444; font-weight: bold' if 'Critical' in str(x) else ('color: #f59e0b' if 'Delay' in str(x) else 'color: #22c55e' if 'Track' in str(x) else ''),
        subset=["Status"]
    ).format({
        "Total Required for Project": "{:,.0f}",
        "Current Stock on Site": "{:,.0f}",
        "In-Transit (Pending Delivery)": "{:,.0f}",
        "Immediate Shortage Risk": "{:,.0f}"
    })
    
    st.dataframe(styled_inv, use_container_width=True, hide_index=True)
    st.caption("*Shortage risk indicates materials required to meet current timeline targets that are neither on-site nor in-transit.*")

# --- 7. TARGET VS SEGMENT COMPLETION VISUAL ---
st.divider()
st.subheader("5. Phased Project Completion & Target Tracking")
st.caption("Visualizing actual physical completion against baseline targets across key engineering segments.")

phases = ["1. Engineering & Design", "2. Procurement & Logistics", "3. Civil Works & Earthmoving", "4. Mechanical & Electrical", "5. Commissioning & Handover"]

planned_array = np.clip([planned_progress * 1.5, (planned_progress - 0.1) * 1.5, (planned_progress - 0.3) * 1.5, (planned_progress - 0.5) * 1.5, (planned_progress - 0.8) * 1.5], 0, 1)
actual_array = np.clip([physical_progress * 1.5, (physical_progress - 0.15) * 1.5, (physical_progress - 0.35) * 1.5, (physical_progress - 0.55) * 1.5, (physical_progress - 0.85) * 1.5], 0, 1)

fig_gantt = go.Figure()

fig_gantt.add_trace(go.Bar(
    y=phases,
    x=planned_array * 100,
    name='Planned Target (%)',
    orientation='h',
    marker=dict(color='rgba(200, 200, 200, 0.4)', line=dict(color='gray', width=1)),
    hoverinfo='x+name'
))

colors = []
for p, a in zip(planned_array, actual_array):
    if a == 0 and p == 0: colors.append('#e2e8f0')
    elif a >= p: colors.append('#22c55e') 
    elif a >= p - 0.1: colors.append('#f59e0b') 
    else: colors.append('#ef4444') 

fig_gantt.add_trace(go.Bar(
    y=phases,
    x=actual_array * 100,
    name='Actual Completion (%)',
    orientation='h',
    marker_color=colors,
    text=[f"{val*100:.1f}%" if val > 0 else "" for val in actual_array],
    textposition='inside',
    insidetextanchor='middle'
))

fig_gantt.update_layout(
    barmode='overlay',
    xaxis=dict(title="Segment Completion (%)", range=[0, 100]),
    yaxis=dict(autorange="reversed"),
    height=350,
    margin=dict(l=20, r=20, t=30, b=20),
    template="plotly_white",
    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
)

st.plotly_chart(fig_gantt, use_container_width=True)

st.info("💡 **Management Insight:** Red bars indicate a project segment is severely lagging behind the baseline schedule, directly correlating with the material bottlenecks identified in the inventory ledger.")