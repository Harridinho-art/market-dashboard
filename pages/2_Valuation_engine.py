import yfinance as yf
import pandas as pd
import streamlit as st

st.title("Stock Valuation Engine")

ticker_input=st.text_input("Enter a stock ticker(e.g., AAPL, MSFT, TSLA): ", value="AAPL")
target_company = yf.Ticker(ticker_input.upper())

income_statement = target_company.income_stmt
balance_sheet = target_company.balance_sheet
cash_flow = target_company.cashflow

revenue = income_statement.loc['Total Revenue']
operating_income = income_statement.loc['Operating Income']

operating_margin = operating_income / revenue

st.subheader("Financial Overview (Latest Year)")
col1, col2 = st.columns(2)

# yfinance returns data for multiple years. 
# We use .iloc[0] to grab the most recent year so it formats beautifully in the metric card.
with col1:
    st.metric(label="Total Revenue", value=f"${revenue.iloc[0]:,.0f}")
with col2:
    st.metric(label="Operating Margin", value=f"{operating_margin.iloc[0] * 100:.2f}%")

fcf= cash_flow.loc['Operating Cash Flow'] + cash_flow.loc['Capital Expenditure']

print("\n---Free Cash Flow---")
print(fcf)

#print("\n---Cash Flow Row Names---")
#print(cash_flow.index.to_list())

latest_fcf = fcf.iloc[0]

growth_rate = 0.05  # Assuming a 5% annual cash flow growth rate for the next 5 years
discount_rate= 0.09  # Assuming a 9% cost of capital (discount rate)
perpetual_growth_rate = 0.025  # Assuming a 2.5% perpetual growth after year 5

projected_fcfs=[]
for year in range(1, 6):
    future_cash=latest_fcf * (1 + growth_rate) ** year
    discounted_cash = future_cash / ((1 + discount_rate) ** year)
    projected_fcfs.append(discounted_cash)

    terminal_value=(projected_fcfs[-1] * (1 + perpetual_growth_rate)) / (discount_rate - perpetual_growth_rate)
    discounted_terminal_value = terminal_value / ((1 + discount_rate) ** 5)

    enterprise_value = sum(projected_fcfs) + discounted_terminal_value

    shares_outstanding = target_company.info['sharesOutstanding']
    current_stock_price = target_company.info['currentPrice']

    estimated_share_price = enterprise_value / shares_outstanding

print("\n================ VALUATION SUMMARY ================")
print(f"current market price: ${current_stock_price:.2f}")
print(f"Estimated intrinsic value: ${estimated_share_price:.2f}")
print(f"===================================================")