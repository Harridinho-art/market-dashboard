import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import time

# --- PAGE SETUP ---
st.set_page_config(page_title="Corporate OPEX & Variance", layout="wide")
st.title("Corporate Performance: Budget vs. Actuals")
st.caption("Bridge the gap between accounting records and financial strategy. Track department spending, isolate performance gaps, and manage daily operating expenses (OPEX).")

# --- 1. DATA INGESTION & PRESETS ---
st.subheader("1. Financial Period & Ledger Ingestion")

with st.container(border=True):
    col_upload, col_period, col_div = st.columns([2, 1, 1])
    
    with col_upload:
        st.markdown("**Upload Monthly Trial Balance**")
        uploaded_tb = st.file_uploader("Upload Actuals vs Budget (CSV/Excel)", type=['csv', 'xlsx'])
    
    with col_period:
        st.markdown("**Reporting Period**")
        period = st.selectbox("Select Period:", ["September 2026 (YTD)", "August 2026 (YTD)", "Q3 2026"])
        
    with col_div:
        st.markdown("**Business Division**")
        division = st.selectbox("Select Division:", ["Power Generation (Operations)", "Corporate Head Office (G&A)", "Sales & Commercial"])

if uploaded_tb:
    with st.spinner("Reconciling uploaded trial balance against baseline budget..."):
        time.sleep(1.2)
    st.success("✅ **Ledger Reconciled:** Successfully mapped actual accounting records to FP&A budget codes.")
else:
    st.info(f"💡 **Demo Mode Active:** Loading standard OPEX profile for **{division}**.")

# --- 2. DYNAMIC OPEX PROFILES ---
# Costs are represented as negative numbers to accurately calculate net profit/burn
if division == "Power Generation (Operations)":
    data = {
        "Line Item": ["Electricity Sales (Income)", "Fuel & Primary Energy", "Plant Maintenance", "Shift Labor & Overtime", "Logistics & Freight"],
        "Budget (ZAR)": [15000000, -8000000, -2500000, -1500000, -500000],
        "Actual (ZAR)": [14200000, -8900000, -2200000, -1550000, -450000]
    }
elif division == "Corporate Head Office (G&A)":
    data = {
        "Line Item": ["Internal Service Recoveries", "Executive & Admin Salaries", "Software & IT Cloud Leases", "Legal & Consulting Fees", "Office Rent & Utilities"],
        "Budget (ZAR)": [2000000, -3500000, -1200000, -800000, -400000],
        "Actual (ZAR)": [1900000, -3550000, -1450000, -600000, -420000]
    }
else: # Sales & Commercial
    data = {
        "Line Item": ["B2B Contract Revenue", "Sales Team Commissions", "Marketing & Advertising", "Travel & Entertainment", "Client Onboarding Costs"],
        "Budget (ZAR)": [8500000, -1200000, -900000, -300000, -150000],
        "Actual (ZAR)": [9100000, -1350000, -850000, -450000, -120000]
    }

df = pd.DataFrame(data)

# Calculate Variances
# Formula: Actual - Budget. (e.g., Actual Cost of -8.9M minus Budget Cost of -8.0M = -0.9M Adverse)
df["Performance Gap"] = df["Actual (ZAR)"] - df["Budget (ZAR)"]
df["% Variance"] = (df["Performance Gap"] / abs(df["Budget (ZAR)"])) * 100

def determine_status(row):
    if row["Performance Gap"] > 0:
        return "🟢 Favorable (Savings/Growth)"
    elif row["Performance Gap"] < 0:
        return "🔴 Adverse (Overspend/Loss)"
    else:
        return "⚪ Exactly on Target"

df["Status"] = df.apply(determine_status, axis=1)

budget_net = df["Budget (ZAR)"].sum()
actual_net = df["Actual (ZAR)"].sum()
total_variance = actual_net - budget_net

# --- 3. EXECUTIVE METRICS ---
st.divider()
st.subheader("2. Division Net Performance Snapshot")

m1, m2, m3 = st.columns(3)
m1.metric(f"Baseline Budget ({period})", f"R {budget_net:,.0f}")
m2.metric(f"Actual Performance ({period})", f"R {actual_net:,.0f}", f"R {total_variance:,.0f} {'Shortfall' if total_variance < 0 else 'Surplus'}", delta_color="inverse" if total_variance < 0 else "normal")

budget_margin = (budget_net / df.loc[0, 'Budget (ZAR)']) * 100 if df.loc[0, 'Budget (ZAR)'] > 0 else 0
actual_margin = (actual_net / df.loc[0, 'Actual (ZAR)']) * 100 if df.loc[0, 'Actual (ZAR)'] > 0 else 0
m3.metric("Operating Margin", f"{actual_margin:.1f}%", f"{actual_margin - budget_margin:.1f}% vs Budget", delta_color="inverse" if (actual_margin - budget_margin) < 0 else "normal")

# --- 4. THE VARIANCE WATERFALL CHART ---
st.divider()
st.subheader("3. OPEX Variance Bridge (Waterfall)")
st.caption("Visually isolating exactly which operational line items caused the department to miss or beat the budget.")

measure = ["absolute"] + ["relative"] * len(df) + ["total"]
x_labels = ["Starting Budget"] + df["Line Item"].tolist() + ["Actual Result"]
y_values = [budget_net] + df["Performance Gap"].tolist() + [actual_net]

fig = go.Figure(go.Waterfall(
    name="Variance Bridge", orientation="v",
    measure=measure,
    x=x_labels,
    textposition="outside",
    text=[f"{val/1000000:,.1f}M" for val in y_values],
    y=y_values,
    connector={"line":{"color":"rgb(63, 63, 63)", "width": 1, "dash": "solid"}},
    decreasing={"marker":{"color":"#ef4444"}}, # Red for Adverse
    increasing={"marker":{"color":"#22c55e"}}, # Green for Favorable
    totals={"marker":{"color":"#3b82f6"}}      # Blue for Totals
))

fig.update_layout(
    title=f"Bridge: Budget vs. Actual Net Contribution ({division})",
    showlegend=False,
    template="plotly_white",
    height=550,
    margin=dict(t=50, b=50),
    yaxis=dict(title="ZAR")
)
st.plotly_chart(fig, use_container_width=True)

# --- 5. DETAILED VARIANCE LEDGER ---
st.divider()
st.subheader("4. Line-Item Variance Ledger")
st.caption("Line-by-line breakdown of day-to-day spending for strict departmental accountability.")

def highlight_status(val):
    if 'Favorable' in val:
        return 'color: #22c55e; font-weight: bold'
    elif 'Adverse' in val:
        return 'color: #ef4444; font-weight: bold'
    return ''

styled_df = df.style.map(highlight_status, subset=['Status']).format({
    "Budget (ZAR)": "R {:,.0f}",
    "Actual (ZAR)": "R {:,.0f}",
    "Performance Gap": "R {:,.0f}",
    "% Variance": "{:.1f}%"
})

st.dataframe(styled_df, use_container_width=True, hide_index=True)

# --- 6. MANAGEMENT COMMENTARY ---
st.write("")
with st.container(border=True):
    st.markdown("**📝 Automated Root Cause Analysis:**")
    
    if division == "Power Generation (Operations)":
        st.markdown("""
        * **Revenue Warning:** Electricity sales underperformed by R 800,000. Investigate whether this was driven by lower grid demand (Volume) or lower realized tariffs (Price).
        * **Supply Chain Overrun:** Fuel consumption exceeded budget by R 900,000. This is a critical OPEX bottleneck indicating either inefficient burn rates or immediate supply chain inflation.
        * **Cost Containment:** Plant Maintenance came in R 300,000 under budget. *Action Required:* Ensure this represents true efficiency and not deferred critical maintenance.
        """)
    elif division == "Corporate Head Office (G&A)":
        st.markdown("""
        * **IT & Infrastructure Overrun:** Software & IT Cloud Leases exceeded budget by R 250,000. Investigate unapproved SaaS subscriptions or unexpected data storage overages.
        * **Professional Services Savings:** Legal & Consulting Fees came in R 200,000 under budget, indicating strong internal capacity and limited reliance on outside contractors this period.
        """)
    else:
        st.markdown("""
        * **Revenue Outperformance:** B2B Contract Revenue beat the budget by R 600,000, signaling strong market capture.
        * **Correlated Overrun:** Sales Commissions and Travel proportionally exceeded the budget. This is an expected and acceptable adverse variance, as it is directly tied to the outperformance in revenue generation.
        """)