import streamlit as st
import pandas as pd
import pdfplumber
import re
from thefuzz import fuzz
from io import BytesIO

st.set_page_config(page_title="Treasury Auditor", layout="wide")

st.title("📊 Automated Treasury Reconciliation Engine")
st.markdown("Upload the internal ledger and the official bank statement. The engine will automatically extract, clean, and cross-reference the data to flag anomalies.")

st.divider()

# 1. The Upload Zones
st.subheader("1. Document Upload")
col1, col2 = st.columns(2)

with col1:
    ledger_file = st.file_uploader("Upload Internal Ledger", type=['csv', 'xlsx'])
    
with col2:
    bank_file = st.file_uploader("Upload Bank Statement", type=['pdf'])

# 2. Execution Trigger
if ledger_file and bank_file:
    st.divider()
    
    if st.button("🚀 Run Automated Audit", use_container_width=True):
        with st.spinner("Executing ETL Pipeline and Fuzzy-Matching Engine..."):
            
            try:
                # --- STEP A: Read Ledger ---
                if ledger_file.name.endswith('.csv'):
                    ledger = pd.read_csv(ledger_file)
                else:
                    ledger = pd.read_excel(ledger_file)
                    
                # --- STEP B: Extract PDF ---
                with pdfplumber.open(bank_file) as pdf:
                    page = pdf.pages[0]
                    extracted_tables = page.extract_tables()
                    if not extracted_tables:
                        st.error("No tables found in the PDF. Please ensure it is a valid format.")
                        st.stop()
                    
                    table_data = extracted_tables[0]
                    headers = table_data[0]
                    transactions = table_data[1:]
                    
                bank = pd.DataFrame(transactions, columns=headers)
                bank.columns = [str(col).replace('\n', ' ').strip() for col in bank.columns]
                
                # --- STEP C: Clean Data ---
                def clean_currency(x):
                    if pd.isna(x) or str(x).strip() == '':
                        return 0.0
                    cleaned_str = re.sub(r'[^\d.]', '', str(x))
                    if not cleaned_str:
                        return 0.0
                    return float(cleaned_str)

                bank['Debit_ZAR'] = bank['Debit (ZAR)'].apply(clean_currency)
                bank['Credit_ZAR'] = bank['Credit (ZAR)'].apply(clean_currency)
                bank['Net_Amount'] = bank['Credit_ZAR'] - bank['Debit_ZAR']
                bank = bank[bank['Description'] != 'OPENING BALANCE']
                
                # --- STEP D: Audit Engine ---
                perfect_matches = []
                anomalies = []
                matched_bank_indices = set()

                for idx, l_row in ledger.iterrows():
                    best_match_score = -1
                    best_match_idx = -1
                    
                    for b_idx, b_row in bank.iterrows():
                        if b_idx in matched_bank_indices:
                            continue
                            
                        score = fuzz.token_set_ratio(l_row['Description'], b_row['Description'])
                        if score > 55 and score > best_match_score:
                            best_match_score = score
                            best_match_idx = b_idx
                            
                    if best_match_idx != -1:
                        b_row = bank.loc[best_match_idx]
                        amount_diff = l_row['Amount'] - b_row['Net_Amount']
                        
                        if amount_diff == 0:
                            perfect_matches.append({
                                'Date': l_row['Date'],
                                'Ledger_Desc': l_row['Description'],
                                'Bank_Desc': b_row['Description'],
                                'Amount': l_row['Amount'],
                                'Match_Confidence': f"{best_match_score}%"
                            })
                            matched_bank_indices.add(best_match_idx)
                        else:
                            anomalies.append({
                                'Audit_Flag': 'Amount Mismatch (Typo / Partial)',
                                'Ledger_Desc': l_row['Description'],
                                'Bank_Desc': b_row['Description'],
                                'Ledger_Amount': l_row['Amount'],
                                'Bank_Amount': b_row['Net_Amount'],
                                'Discrepancy': amount_diff
                            })
                            matched_bank_indices.add(best_match_idx)
                    else:
                        anomalies.append({
                            'Audit_Flag': 'Phantom Ledger Entry (Not in Bank)',
                            'Ledger_Desc': l_row['Description'],
                            'Bank_Desc': 'N/A',
                            'Ledger_Amount': l_row['Amount'],
                            'Bank_Amount': 0,
                            'Discrepancy': l_row['Amount']
                        })

                for b_idx, b_row in bank.iterrows():
                    if b_idx not in matched_bank_indices:
                        anomalies.append({
                            'Audit_Flag': 'Missing in Ledger (Unrecorded)',
                            'Ledger_Desc': 'N/A',
                            'Bank_Desc': b_row['Description'],
                            'Ledger_Amount': 0,
                            'Bank_Amount': b_row['Net_Amount'],
                            'Discrepancy': -b_row['Net_Amount']
                        })

                # --- STEP E: Render UI ---
                st.success("✅ Audit Complete!")
                
                st.subheader("⚠️ Detected Anomalies")
                if anomalies:
                    st.dataframe(pd.DataFrame(anomalies), use_container_width=True)
                else:
                    st.info("No anomalies detected. The books are perfectly balanced.")
                
                with st.expander("View Reconciled Matches"):
                    st.dataframe(pd.DataFrame(perfect_matches), use_container_width=True)
                    
                # --- STEP F: Export to Excel in Memory ---
                output = BytesIO()
                with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                    pd.DataFrame(perfect_matches).to_excel(writer, sheet_name='Reconciled', index=False)
                    pd.DataFrame(anomalies).to_excel(writer, sheet_name='Anomalies', index=False)
                output.seek(0)
                
                st.download_button(
                    label="📥 Download Official Audit Report (.xlsx)",
                    data=output,
                    file_name="Automated_Audit_Report.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    type="primary"
                )

            except Exception as e:
                st.error(f"An error occurred during execution: {e}")