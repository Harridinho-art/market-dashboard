import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go

st.set_page_config(page_title="Credit & Refinancing Engine", layout="wide")
st.title("Credit Risk & Debt Refinancing Engine")
st.markdown(
    "Institutional credit stress-testing: debt maturity cliffs, credit spread blowouts, "
    "bank covenant headroom, and collateral haircuts."
)

# --- 1. SIDEBAR: MULTI-DIMENSIONAL CREDIT SHOCKS ---
st.sidebar.header("Borrower Selection")
st.sidebar.caption("Enter JSE stocks (.JO) or global tickers.")
ticker = st.sidebar.text_input("Ticker Symbol:", value="EXX.JO").upper()

st.sidebar.divider()
st.sidebar.subheader("1. Debt Maturity & Refinancing")
refinance_pct = st.sidebar.slider(
    "Debt Expiring in Cycle (%)", 
    min_value=10, max_value=100, value=35, step=5,
    help="Percentage of total balance sheet debt maturing and needing refinancing."
)
old_rate = st.sidebar.slider(
    "Historical Borrowing Cost (%)", 
    min_value=1.0, max_value=15.0, value=6.5, step=0.25,
    help="The blended interest rate secured on existing facilities."
)

st.sidebar.divider()
st.sidebar.subheader("2. Macro & Credit Spread Shocks")
base_rate_shock_bps = st.sidebar.slider(
    "Central Bank Rate Hike (bps)", 
    min_value=0, max_value=500, value=150, step=25,
    help="100 bps = 1.0%. Simulates SARB / benchmark rate tightening."
) / 10000

credit_spread_bps = st.sidebar.slider(
    "Credit Spread / Transition Penalty (bps)", 
    min_value=0, max_value=600, value=250, step=25,
    help="Credit risk premium or bank GLAA restriction penalty above benchmark."
) / 10000

st.sidebar.divider()
st.sidebar.subheader("3. Asset & Operational Shock")
ebitda_shock_pct = st.sidebar.slider(
    "EBITDA / Profit Shock (%)", 
    min_value=-50, max_value=10, value=-15, step=5,
    help="Simulates market downturn or demand drop hitting operating earnings."
)
asset_haircut_pct = st.sidebar.slider(
    "Collateral / Asset Haircut (%)", 
    min_value=0, max_value=50, value=20, step=5,
    help="Simulates asset stranding, depreciation, or liquidation discount on assets."
)

# --- 2. DATA EXTRACTION ENGINE ---
@st.cache_data(ttl=3600)
def fetch_debt_fundamentals(t_symbol):
    try:
        t = yf.Ticker(t_symbol)
        bs = t.balance_sheet
        inc = t.income_stmt
        info = t.info

        # Localized Currency Formatting
        curr_code = info.get('financialCurrency', info.get('currency', 'USD'))
        curr_sym = {'ZAR': 'R ', 'USD': '$', 'GBP': '£', 'EUR': '€'}.get(curr_code, curr_code + ' ')

        # Balance Sheet Items
        total_debt = bs.loc['Total Debt'].iloc[0] if 'Total Debt' in bs.index else 0
        cash = bs.loc['Cash And Cash Equivalents'].iloc[0] if 'Cash And Cash Equivalents' in bs.index else 0
        total_assets = bs.loc['Total Assets'].iloc[0] if 'Total Assets' in bs.index else 1
        current_assets = bs.loc['Current Assets'].iloc[0] if 'Current Assets' in bs.index else 0
        current_liab = bs.loc['Current Liabilities'].iloc[0] if 'Current Liabilities' in bs.index else 1

        # Income Statement Items
        rev = inc.loc['Total Revenue'].iloc[0] if 'Total Revenue' in inc.index else 1
        ebit = inc.loc['EBIT'].iloc[0] if 'EBIT' in inc.index else 0
        net_inc = inc.loc['Net Income'].iloc[0] if 'Net Income' in inc.index else 0
        interest_exp = abs(inc.loc['Interest Expense'].iloc[0]) if 'Interest Expense' in inc.index else 1

        # Approximation of EBITDA (EBIT + estimated 5% assets as D&A if unavailable)
        depr = abs(inc.loc['Reconciled Depreciation'].iloc[0]) if 'Reconciled Depreciation' in inc.index else (total_assets * 0.04)
        ebitda = ebit + depr

        company_name = info.get('shortName', t_symbol)

        return {
            "Name": company_name, "Symbol": curr_sym, "Total Debt": total_debt,
            "Cash": cash, "Total Assets": total_assets, "Current Assets": current_assets,
            "Current Liab": current_liab, "Revenue": rev, "EBIT": ebit,
            "EBITDA": ebitda, "Net Income": net_inc, "Base Interest": interest_exp
        }
    except Exception as e:
        return None

with st.spinner(f"Extracting credit structures for {ticker}..."):
    data = fetch_debt_fundamentals(ticker)

if not data or data["Total Debt"] == 0:
    st.error(f"Could not load debt metrics for '{ticker}'. Company may have zero reported debt or invalid ticker.")
    st.stop()

sym = data["Symbol"]

# --- 3. REFINANCING MATHEMATICS ---
# 1. Maturing Debt Volume
maturing_debt = data["Total Debt"] * (refinance_pct / 100.0)
untouched_debt = data["Total Debt"] - maturing_debt

# 2. Refinanced Borrowing Rate: Old Base + Central Bank Shock + Credit Spread Blowout
new_refinanced_rate = (old_rate / 100.0) + base_rate_shock_bps + credit_spread_bps

# 3. Interest Cost Evolution
old_maturing_interest = maturing_debt * (old_rate / 100.0)
new_maturing_interest = maturing_debt * new_refinanced_rate
refinancing_cost_delta = new_maturing_interest - old_maturing_interest

# Total New Annual Interest
stressed_total_interest = data["Base Interest"] + refinancing_cost_delta

# 4. Earnings & Coverage Shocks
stressed_ebitda = data["EBITDA"] * (1.0 + (ebitda_shock_pct / 100.0))
stressed_ebit = data["EBIT"] * (1.0 + (ebitda_shock_pct / 100.0))
stressed_net_income = data["Net Income"] - refinancing_cost_delta

# Solvency Covenants
base_icr = data["EBIT"] / data["Base Interest"] if data["Base Interest"] > 0 else 999.0
stressed_icr = stressed_ebit / stressed_total_interest if stressed_total_interest > 0 else 999.0

base_net_debt = data["Total Debt"] - data["Cash"]
base_leverage = base_net_debt / data["EBITDA"] if data["EBITDA"] > 0 else 999.0
stressed_leverage = base_net_debt / stressed_ebitda if stressed_ebitda > 0 else 999.0

# 5. Collateral & Stranded Asset Coverage
stressed_asset_value = data["Total Assets"] * (1.0 - (asset_haircut_pct / 100.0))
base_asset_coverage = (data["Total Assets"] / data["Total Debt"]) if data["Total Debt"] > 0 else 999.0
stressed_asset_coverage = (stressed_asset_value / data["Total Debt"]) if data["Total Debt"] > 0 else 999.0

# --- 4. SECTION 1: BORROWER SNAPSHOT & EXECUTIVE COVENANT SCORECARD ---
st.subheader(f"Borrower: {data['Name']}")
st.caption(f"Capital Structure & Liquidity Base (Figures in {sym})")

b1, b2, b3, b4 = st.columns(4)
with b1:
    st.metric("Total Debt Balance", f"{sym}{data['Total Debt']:,.0f}")
with b2:
    st.metric("Cash & Equivalents", f"{sym}{data['Cash']:,.0f}")
with b3:
    st.metric("Maturing Debt Under Test", f"{sym}{maturing_debt:,.0f}", f"{refinance_pct}% of Book")
with b4:
    st.metric("New Refinanced Rate", f"{new_refinanced_rate * 100:.2f}%", f"+{(new_refinanced_rate - (old_rate/100))*10000:.0f} bps")

st.divider()
st.subheader("1. Institutional Covenant Health Check")
st.caption("Standard commercial banking limits: Interest Coverage Ratio (ICR) >= 2.5x | Leverage <= 3.5x.")

c1, c2, c3 = st.columns(3)
with c1:
    icr_status = "Safe" if stressed_icr >= 3.0 else ("Borderline" if stressed_icr >= 2.5 else "CRITICAL BREACH")
    st.metric(
        "Stressed Interest Cover (ICR)", 
        f"{stressed_icr:.2f}x", 
        f"Baseline: {base_icr:.2f}x ({icr_status})",
        delta_color="normal" if stressed_icr >= 2.5 else "inverse"
    )
with c2:
    lev_status = "Safe" if stressed_leverage <= 3.0 else ("Elevated" if stressed_leverage <= 3.5 else "CRITICAL BREACH")
    st.metric(
        "Stressed Leverage (Net Debt/EBITDA)", 
        f"{stressed_leverage:.2f}x", 
        f"Baseline: {base_leverage:.2f}x ({lev_status})",
        delta_color="normal" if stressed_leverage <= 3.5 else "inverse"
    )
with c3:
    cov_status = "Adequate" if stressed_asset_coverage >= 1.5 else "Collateral Risk"
    st.metric(
        "Stressed Asset Coverage", 
        f"{stressed_asset_coverage:.2f}x", 
        f"Haircut Value: {sym}{stressed_asset_value:,.0f}",
        delta_color="normal" if stressed_asset_coverage >= 1.5 else "inverse"
    )

# --- 5. SECTION 2: THE REFINANCING EARNINGS DRAIN ---
st.divider()
st.subheader("2. Refinancing Cost Drag & Profit Drain")
st.caption("Annual incremental interest expense required to service the debt maturity wall.")

col_left, col_right = st.columns([1, 2])

with col_left:
    st.metric("New Incremental Interest Cost", f"{sym}{refinancing_cost_delta:,.0f}")
    st.metric("Total Stressed Interest Burden", f"{sym}{stressed_total_interest:,.0f}")
    earnings_wipeout_pct = (refinancing_cost_delta / data["Net Income"] * 100) if data["Net Income"] > 0 else 0
    st.metric("Net Earnings Erosion", f"{earnings_wipeout_pct:.1f}%", delta_color="inverse")

with col_right:
    fig_bar = go.Figure()
    fig_bar.add_trace(go.Bar(
        name="Operating Profit (EBIT)",
        x=["Baseline Scenario", "Refinanced Stress Scenario"],
        y=[data["EBIT"], stressed_ebit],
        marker_color="#2563eb"
    ))
    fig_bar.add_trace(go.Bar(
        name="Total Debt Service (Interest)",
        x=["Baseline Scenario", "Refinanced Stress Scenario"],
        y=[data["Base Interest"], stressed_total_interest],
        marker_color="#ef4444"
    ))
    fig_bar.update_layout(
        barmode="group",
        template="plotly_white",
        yaxis_title=f"Capital ({sym})",
        margin=dict(t=20, b=20),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
    )
    st.plotly_chart(fig_bar, use_container_width=True)

# --- 6. SECTION 3: INSTITUTIONAL SENSITIVITY MATRIX (SARB / PRUDENTIAL VIEW) ---
st.divider()
st.subheader("3. Macro Stress Matrix: Interest Coverage Ratio (ICR)")
st.caption(
    "Evaluating borrower solvency under simultaneous SARB Repo rate hikes and credit spread blowouts. "
    "Values below 2.5x represent technical debt covenant default."
)

repo_shocks = [0, 100, 200, 300, 400] # in bps
spread_shocks = [0, 100, 200, 300, 400, 500] # in bps

matrix_data = []
for r_bps in repo_shocks:
    row = []
    for s_bps in spread_shocks:
        sim_new_rate = (old_rate / 100.0) + (r_bps / 10000.0) + (s_bps / 10000.0)
        sim_cost_delta = maturing_debt * (sim_new_rate - (old_rate / 100.0))
        sim_tot_interest = data["Base Interest"] + sim_cost_delta
        sim_icr = stressed_ebit / sim_tot_interest if sim_tot_interest > 0 else 0
        row.append(round(sim_icr, 2))
    matrix_data.append(row)

df_matrix = pd.DataFrame(
    matrix_data,
    index=[f"+{r} bps Repo" for r in repo_shocks],
    columns=[f"+{s} bps Spread" for s in spread_shocks]
)

def highlight_covenant_breaches(val):
    if val < 2.5:
        return 'background-color: #fee2e2; color: #991b1b; font-weight: bold' # Red (Breach)
    elif val < 3.0:
        return 'background-color: #fef9c3; color: #854d0e' # Yellow (Borderline)
    else:
        return 'background-color: #dcfce7; color: #166534' # Green (Safe)

# Format with 'x' and handle both Pandas versions (.map vs .applymap)
styler = df_matrix.style.format("{:.2f}x")
if hasattr(styler, "map"):
    styled_matrix = styler.map(highlight_covenant_breaches)
else:
    styled_matrix = styler.applymap(highlight_covenant_breaches)

st.dataframe(styled_matrix, use_container_width=True)
st.caption("Legend: 🟩 Safe (≥ 3.0x) | 🟨 Borderline (2.5x - 3.0x) | 🟥 Covenant Breach (< 2.5x)")