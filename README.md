# Financial Support System (FP&A Suite)

A full-stack Python web application engineered to automate finance, I built it with inspiration from Xero and SAGE accounting, and tried creating my own Accounting Software system that is relevant to my qualication and skills.. 

Built to bridge the gap between static IFRS accounting (historical data) and dynamic Financial Planning & Analysis (FP&A) using live market data and automated ledger parsing.

### ⚙️ Core Engines & Features

* **Corporate Liquidity & Working Capital Engine:** Analyzes the Cash Conversion Cycle (CCC), visualizes cash gaps via Gantt timelines, and quantifies short-term funding requirements to prevent overtrading.
* **IFRS 9 Debtors & Credit Risk Engine:** Automates Accounts Receivable aging and calculates Expected Credit Loss (ECL) provisioning to flag severe capital trapping.
* **Debt Refinancing & Covenant Stress Tester:** Institutional credit engine that stresses Interest Coverage Ratios (ICR) and Leverage against central bank (SARB) rate hikes and credit spread blowouts.
* **Management CVP Engine:** Parses raw accounting ledgers to automatically classify fixed vs. variable costs, projecting break-even horizons and Degree of Operating Leverage (DOL).
* **Equity & Dividend Forecaster:** Real-time JSE and global stock stress-testing (via `yfinance`) against macroeconomic shocks.

### 🛠️ Tech Stack
* **Language:** Python
* **Frontend/Framework:** Streamlit (Focus on clean, intuitive financial UI/UX)
* **Data Processing:** Pandas, NumPy
* **Data Visualization:** Plotly (Interactive waterfalls, funnels, and dynamic timelines)
* **Market API:** Yahoo Finance (`yfinance`)

**Live Application:** [https://market-dashboard-eqym2pkmtoce26x5kkrhwz.streamlit.app/Working_Capital_Engine] 
