import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go

# --- PAGE SETUP ---
st.set_page_config(page_title="Project Finance & Capex Tracker", layout="wide")
st.title("Project Finance & Capital Expenditure (CAPEX) Manager")
st.caption("A multi-industry project tracker for managing budgets, contractor commitments, physical site progress, and cash burn.")

# --- INDUSTRY PRESETS ---
# Practical datasets covering Mining, Power, Renewable Energy, and Heavy Construction
PROJECT_CATALOG = {
    "Mining: Open-Cast Pit Box-Cut & Haul Road": {
        "sector": "Mining",
        "baseline_budget": 350_000_000,
        "approved_variations": 35_000_000,     # Extra rock excavation, diesel inflation
        "contracts_signed": 310_000_000,       # Committed to earthmoving contractors
        "invoices_paid": 220_000_000,          # Actual cash out
        "physical_progress": 0.65,              # 65% physical digging done
        "planned_progress": 0.70,               # Should be at 70%
        "loan_interest_during_build": 14_000_000,
        "retention_rate": 0.05,                 # 5% withheld until handover
        "duration_months": 18,
        "current_month": 12
    },
    "Power Utility: Coal Plant Scrubber Retrofit": {
        "sector": "Utilities & Power",
        "baseline_budget": 850_000_000,
        "approved_variations": 95_000_000,     # Structural modifications
        "contracts_signed": 780_000_000,
        "invoices_paid": 520_000_000,
        "physical_progress": 0.52,
        "planned_progress": 0.60,
        "loan_interest_during_build": 38_000_000,
        "retention_rate": 0.10,                 # 10% retention
        "duration_months": 24,
        "current_month": 14
    },
    "Renewables: 75MW Solar PV & Battery Storage": {
        "sector": "Renewable Energy",
        "baseline_budget": 620_000_000,
        "approved_variations": -15_000_000,    # Equipment procurement savings
        "contracts_signed": 580_000_000,
        "invoices_paid": 410_000_000,
        "physical_progress": 0.78,
        "planned_progress": 0.72,
        "loan_interest_during_build": 19_000_000,
        "retention_rate": 0.05,
        "duration_months": 14,
        "current_month": 10
    },
    "Civil Infrastructure: Heavy Rail & Bulk Loading Bay": {
        "sector": "Construction & Logistics",
        "baseline_budget": 240_000_000,
        "approved_variations": 18_000_000,
        "contracts_signed": 210_000_000,
        "invoices_paid": 140_000_000,
        "physical_progress": 0.55,
        "planned_progress": 0.55,
        "loan_interest_during_build": 8_500_000,
        "retention_rate": 0.08,
        "duration_months": 16,
        "current_month": 9
    }
}

# --- CONTROL PANEL ---
st.subheader("1. Select Project & Adjust Key Parameters")

col_sel, col_mode = st.columns([2, 1])
with col_sel:
    project_choice = st.selectbox("Active Capital Project:", list(PROJECT_CATALOG.keys()))
    proj = PROJECT_CATALOG[project_choice]

with col_mode:
    st.write(f"**Industry Sector:** {proj['sector']}")
    st.write(f"**Timeline:** Month {proj['current_month']} of {proj['duration_months']}")

# Editable adjustments for real-time scenario testing
with st.expander("Adjust Project Inputs (Run Real-Time Scenarios)", expanded=False):
    c_in1, c_in2, c_in3, c_in4 = st.columns(4)
    baseline = c_in1.number_input("Original Budget (ZAR)", value=float(proj['baseline_budget']), step=1_000_000.0)
    variations = c_in2.number_input("Approved Scope Changes (+/- ZAR)", value=float(proj['approved_variations']), step=500_000.0)
    committed = c_in3.number_input("Contracts Signed / POs (ZAR)", value=float(proj['contracts_signed']), step=1_000_000.0)
    paid = c_in4.number_input("Invoices Paid Out (ZAR)", value=float(proj['invoices_paid']), step=1_000_000.0)
    
    c_in5, c_in6, c_in7, c_in8 = st.columns(4)
    phys_pct = c_in5.slider("Actual Work Completed On-Site (%)", 1, 100, int(proj['physical_progress'] * 100)) / 100
    plan_pct = c_in6.slider("Planned Target for Today (%)", 1, 100, int(proj['planned_progress'] * 100)) / 100
    ret_rate = c_in7.slider("Contractor Retention Held (%)", 0, 15, int(proj['retention_rate'] * 100)) / 100
    idc = c_in8.number_input("Loan Interest During Construction (ZAR)", value=float(proj['loan_interest_during_build']), step=500_000.0)

# --- CORE PROJECT FINANCE CALCULATIONS ---
# 1. Total Current Budget
revised_budget = baseline + variations

# 2. Earned Value (Value of physical work delivered in money terms)
work_value_delivered = revised_budget * phys_pct
planned_value_target = revised_budget * plan_pct

# 3. Efficiency Ratios (Plain English)
# Budget Efficiency: Are we paying more than the work done?
budget_efficiency = work_value_delivered / paid if paid > 0 else 1.0
# Schedule Efficiency: Are we moving faster or slower than the plan?
schedule_efficiency = work_value_delivered / planned_value_target if planned_value_target > 0 else 1.0

# 4. Projected Total Cost at Finish
expected_final_cost = revised_budget / budget_efficiency if budget_efficiency > 0 else revised_budget
projected_overrun = expected_final_cost - revised_budget

# 5. Contractual Protections & Available Cash
retention_money_held = paid * ret_rate
uncommitted_budget = revised_budget - committed
total_asset_cost_to_date = paid + idc  # Real cash + capitalized loan interest

# --- EXECUTIVE SUMMARY METRICS ---
st.divider()
st.subheader("2. Project Financial Health Overview")

m1, m2, m3, m4 = st.columns(4)
m1.metric(
    "Total Revised Budget",
    f"R {revised_budget / 1_000_000:,.1f} M",
    f"{variations / 1_000_000:+,.1f} M scope changes"
)
m2.metric(
    "Asset Cost Built to Date",
    f"R {total_asset_cost_to_date / 1_000_000:,.1f} M",
    f"R {idc / 1_000_000:,.1f} M loan interest added"
)
m3.metric(
    "Forecasted Cost at Finish",
    f"R {expected_final_cost / 1_000_000:,.1f} M",
    f"R {projected_overrun / 1_000_000:+,.1f} M {'overrun' if projected_overrun > 0 else 'savings'}",
    delta_color="inverse"
)
m4.metric(
    "Contractor Retention Held",
    f"R {retention_money_held / 1_000_000:,.2f} M",
    f"{int(ret_rate * 100)}% held back for safety"
)

# --- STATUS CARDS ---
st.write("")
stat_col1, stat_col2, stat_col3 = st.columns(3)

with stat_col1:
    with st.container(border=True):
        st.markdown("**Budget Health**")
        if budget_efficiency >= 1.0:
            st.success(f"**Under Budget** ({budget_efficiency:.2f}x efficiency)")
            st.caption("You are getting more physical site progress per Rand spent than planned.")
        elif budget_efficiency >= 0.90:
            st.warning(f"**Minor Overrun** ({budget_efficiency:.2f}x efficiency)")
            st.caption("Expenses are tracking slightly ahead of actual work delivered.")
        else:
            st.error(f"**Severe Overrun** ({budget_efficiency:.2f}x efficiency)")
            st.caption("Cash is burning faster than physical construction. Site review required.")

with stat_col2:
    with st.container(border=True):
        st.markdown("**Schedule Health**")
        if schedule_efficiency >= 1.0:
            st.success(f"**Ahead of Schedule** ({schedule_efficiency:.2f}x pace)")
            st.caption("Site teams are tracking ahead of the baseline delivery milestone.")
        elif schedule_efficiency >= 0.90:
            st.warning(f"**Slight Delay** ({schedule_efficiency:.2f}x pace)")
            st.caption("Slight delays on site. Manageable without impacting final commissioning.")
        else:
            st.error(f"**Critical Delay** ({schedule_efficiency:.2f}x pace)")
            st.caption("Work delivered is significantly behind schedule. Risk of penalty claims.")

with stat_col3:
    with st.container(border=True):
        st.markdown("**Capital Remaining**")
        if uncommitted_budget >= 0:
            st.info(f"**R {uncommitted_budget / 1_000_000:,.1f} M Available**")
            st.caption("Free budget remaining to issue new tenders or cover site emergencies.")
        else:
            st.error(f"**R {abs(uncommitted_budget) / 1_000_000:,.1f} M Over-Committed**")
            st.caption("Contracts signed exceed the total approved budget. Halt new purchase orders.")

# --- DETAILED LEDGER BREAKDOWN ---
st.divider()
st.subheader("3. Project Cost Breakdown & Contract Ledger")

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
        baseline,
        variations,
        revised_budget,
        committed,
        paid,
        work_value_delivered,
        retention_money_held,
        idc,
        total_asset_cost_to_date
    ],
    "% of Total Budget": [
        f"{(baseline / revised_budget) * 100:.1f}%",
        f"{(variations / revised_budget) * 100:.1f}%",
        "100.0%",
        f"{(committed / revised_budget) * 100:.1f}%",
        f"{(paid / revised_budget) * 100:.1f}%",
        f"{(work_value_delivered / revised_budget) * 100:.1f}%",
        f"{(retention_money_held / revised_budget) * 100:.1f}%",
        f"{(idc / revised_budget) * 100:.1f}%",
        f"{(total_asset_cost_to_date / revised_budget) * 100:.1f}%"
    ],
    "Practical Meaning for Management": [
        "Starting baseline approved by board/lenders",
        "Formal adjustments from unforeseen engineering changes",
        "The current total allowable spend limit",
        "Money legally promised to suppliers and contractors",
        "Real cash that has left the project bank account",
        "Real worth of concrete, steel, and earth moved on site",
        "Safety deposit held back to guarantee quality work",
        "Loan interest added straight to asset value instead of expense",
        "What this asset is actually worth on the books today"
    ]
})

st.dataframe(
    breakdown_data.style.format({"Amount (ZAR)": "R {:,.0f}"}),
    use_container_width=True,
    hide_index=True
)

# --- CAPITAL BURN S-CURVE ---
st.divider()
st.subheader("4. Cash Burn Curve (Planned Target vs Real Spend)")
st.caption("Visualizing the traditional S-Curve: how cash is projected to leave the bank compared to real contractor claims.")

duration = proj['duration_months']
curr_m = proj['current_month']
months = np.arange(1, duration + 1)

# Generate a realistic project spend S-Curve (Sigmoid distribution)
# Slow ramp-up at start, heavy spending in middle, taper off at commissioning
midpoint = duration / 2
steepness = 0.4
planned_weights = 1 / (1 + np.exp(-steepness * (months - midpoint)))
# Normalize to start near 0 and finish at 100% of revised budget
planned_weights = (planned_weights - planned_weights[0]) / (planned_weights[-1] - planned_weights[0])
planned_spend = planned_weights * revised_budget

# Actual spend curve up to the current month
actual_spend = []
for m in months:
    if m <= curr_m:
        # Scale actual spend smoothly up to current paid amount
        ratio = (m / curr_m) ** 1.15
        actual_spend.append(ratio * paid)
    else:
        actual_spend.append(np.nan)

# Forecast to project end from current position
forecast_spend = []
for m in months:
    if m < curr_m:
        forecast_spend.append(np.nan)
    elif m == curr_m:
        forecast_spend.append(paid)
    else:
        remaining_months = duration - curr_m
        progress_remaining = m - curr_m
        forecast_val = paid + (expected_final_cost - paid) * (progress_remaining / remaining_months)
        forecast_spend.append(forecast_val)

fig_scurve = go.Figure()

# Planned Target
fig_scurve.add_trace(go.Scatter(
    x=months, y=planned_spend / 1_000_000,
    mode='lines',
    name='Planned Target (Baseline S-Curve)',
    line=dict(color='gray', dash='dash', width=2)
))

# Real Invoiced Cash
fig_scurve.add_trace(go.Scatter(
    x=months, y=np.array(actual_spend) / 1_000_000,
    mode='lines+markers',
    name='Actual Cash Paid Out',
    line=dict(color='#2563eb', width=3),
    marker=dict(size=6)
))

# Projected Run Rate
fig_scurve.add_trace(go.Scatter(
    x=months, y=np.array(forecast_spend) / 1_000_000,
    mode='lines',
    name='Forecasted Finish (Current Burn Rate)',
    line=dict(color='#ef4444', dash='dot', width=2)
))

fig_scurve.add_vline(x=curr_m, line_dash="solid", line_color="#10b981", annotation_text=f"Current Status (Month {curr_m})")

fig_scurve.update_layout(
    xaxis=dict(title="Project Month", tickmode='linear', tick0=1, dtick=1),
    yaxis=dict(title="Cumulative Spend (Million ZAR)"),
    template="plotly_white",
    height=450,
    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
    margin=dict(l=20, r=20, t=30, b=20)
)

st.plotly_chart(fig_scurve, use_container_width=True)

# --- PRACTICAL INSIGHT NOTE ---
st.info("""
**Management Rule of Thumb:** 
* **Committed vs Actual:** Never evaluate budget health using cash paid alone. If 90% of your budget is tied up in signed contracts, you cannot issue new work even if the cash has not left your account.
* **Retention Safety Net:** Keeping 5% to 10% withheld from contractor certificates ensures you have funds to fix defective work if a vendor defaults before final sign-off.
""")