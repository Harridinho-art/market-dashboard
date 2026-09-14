import yfinance as yf
import pandas as pd
import streamlit as st

st.title("Stock Valuation Engine")
ticker_input = st.text_input("Enter a stock ticker (e.g., AAPL, MSFT, TSLA): ", value="AAPL")

# Add a loading spinner while fetching data
with st.spinner(f"Pulling financial data and calculating DCF for {ticker_input.upper()}..."):
    target_company = yf.Ticker(ticker_input.upper())

    income_statement = target_company.income_stmt
    balance_sheet = target_company.balance_sheet
    cash_flow = target_company.cashflow

    revenue = income_statement.loc['Total Revenue']
    operating_income = income_statement.loc['Operating Income']
    operating_margin = operating_income / revenue

    st.subheader("Financial Overview (Latest Year)")
    col1, col2 = st.columns(2)

    with col1:
        st.metric(label="Total Revenue", value=f"${revenue.iloc[0]:,.0f}")
    with col2:
        st.metric(label="Operating Margin", value=f"{operating_margin.iloc[0] * 100:.2f}%")

    # --- CASH FLOW VISUALIZATION ---
    fcf = cash_flow.loc['Operating Cash Flow'] + cash_flow.loc['Capital Expenditure']
    latest_fcf = fcf.iloc[0]

    st.divider()
    st.subheader("Historical Free Cash Flow")
    
    # Drop missing data and sort chronologically (oldest to newest)
    fcf_clean = fcf.dropna().iloc[::-1]
    
    # Create dynamic columns for however many years of data yfinance returns
    fcf_cols = st.columns(len(fcf_clean))
    
    for i, (date, value) in enumerate(fcf_clean.items()):
        # Calculate Year-over-Year (YoY) growth for the delta indicator
        if i == 0:
            yoy_delta = None
        else:
            prev_val = fcf_clean.iloc[i-1]
            yoy = ((value - prev_val) / abs(prev_val)) * 100
            yoy_delta = f"{yoy:.2f}% YoY"
            
        with fcf_cols[i]:
            # Scale to billions for clean UI rendering
            st.metric(
                label=f"FY {date.year}", 
                value=f"${value / 1e9:.2f}B", 
                delta=yoy_delta
            )

    # --- INTERACTIVE DCF ASSUMPTIONS ---
    st.divider()
    st.subheader("DCF Model Assumptions")
    st.caption("Adjust the parameters below to stress-test the valuation.")
    
    colA, colB, colC = st.columns(3)
    with colA:
        growth_rate = st.number_input("5-Year Growth Rate (%)", value=5.0, step=0.5) / 100
        
    with colB:
        # PHASE 1: Auto-WACC (CAPM)
        auto_wacc = st.checkbox("Auto-Calculate WACC (CAPM)")
        if auto_wacc:
            # Fetch 10-Year Treasury Yield for Risk-Free Rate
            try:
                tnx = yf.Ticker("^TNX")
                risk_free_rate = tnx.info.get('regularMarketPreviousClose', 4.0) / 100
            except:
                risk_free_rate = 0.042 # Fallback to 4.2% if API fails
            
            # Fetch stock beta
            beta = target_company.info.get('beta', 1.0)
            market_risk_premium = 0.055 # Standard 5.5% ERP
            
            # Calculate CAPM
            discount_rate = risk_free_rate + (beta * market_risk_premium)
            
            st.metric("Calculated WACC", f"{discount_rate * 100:.2f}%", 
                      help=f"Risk-Free Rate: {risk_free_rate*100:.2f}% | Beta: {beta}")
        else:
            discount_rate = st.number_input("Discount Rate/WACC (%)", value=9.0, step=0.5) / 100
            
    with colC:
        perpetual_growth_rate = st.number_input("Perpetual Growth (%)", value=2.5, step=0.1) / 100

    # --- DCF MATH ---
    projected_fcfs = []
    for year in range(1, 6):
        future_cash = latest_fcf * (1 + growth_rate) ** year
        discounted_cash = future_cash / ((1 + discount_rate) ** year)
        projected_fcfs.append(discounted_cash)

    terminal_value = (projected_fcfs[-1] * (1 + perpetual_growth_rate)) / (discount_rate - perpetual_growth_rate)
    discounted_terminal_value = terminal_value / ((1 + discount_rate) ** 5)

    enterprise_value = sum(projected_fcfs) + discounted_terminal_value

    # Safely pull shares outstanding and current price
    shares_outstanding = target_company.info.get('sharesOutstanding', 1)
    current_stock_price = target_company.info.get('currentPrice', 1)

    estimated_share_price = enterprise_value / shares_outstanding

    # --- VALUATION SUMMARY METRICS ---
    st.divider()
    st.subheader("Valuation Output")
    
    # Calculate margin of safety / upside
    upside_percentage = ((estimated_share_price - current_stock_price) / current_stock_price) * 100

    val_col1, val_col2, val_col3 = st.columns(3)
    with val_col1:
        st.metric("Current Market Price", f"${current_stock_price:,.2f}")
    with val_col2:
        # Dynamic Delta: Shows Green if undervalued, Red if overvalued
        st.metric("Estimated Intrinsic Value", f"${estimated_share_price:,.2f}", 
                  delta=f"{upside_percentage:.2f}% Implied Upside", 
                  delta_color="normal")
    with val_col3:
        st.metric("Implied Enterprise Value", f"${enterprise_value / 1e9:,.2f}B")