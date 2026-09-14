import pandas as pd
from thefuzz import fuzz
import numpy as np
import re

print("🔍 Initiating CIMA-Aligned Automated Reconciliation Engine for JUNE...")

# 1. Generate Vanguard Logistics' Internal Ledger for June
ledger_data = [
    {'Date': '02/06/2026', 'Description': 'Engen Rosebank Fuel', 'Amount': -850.00},
    {'Date': '04/06/2026', 'Description': 'INV-091 Clearance', 'Amount': 25000.00},
    {'Date': '06/06/2026', 'Description': 'Vida e Caffe Meeting', 'Amount': -240.00},
    {'Date': '10/06/2026', 'Description': 'SARS PAYE', 'Amount': -14500.00},
    {'Date': '14/06/2026', 'Description': 'Checkers Office Supplies', 'Amount': -1250.00},
    {'Date': '15/06/2026', 'Description': 'June Payroll', 'Amount': -42000.00},
    {'Date': '18/06/2026', 'Description': 'Vodacom Contract', 'Amount': -1800.00},
    # Trap 1: We are completely missing the second Engen charge from 21/06
    # Trap 2: Amount mismatch on the consulting fee (18,500 instead of 18,000)
    {'Date': '25/06/2026', 'Description': 'Consulting Services EFT', 'Amount': -18500.00},
    {'Date': '27/06/2026', 'Description': 'INV-092 Clearance', 'Amount': 20000.00},
    # Trap 3: Phantom Entry that isn't on the bank statement
    {'Date': '28/06/2026', 'Description': 'Staff Team Building', 'Amount': -3000.00},
    {'Date': '29/06/2026', 'Description': 'AWS Cloud Hosting', 'Amount': -460.00}
]
ledger = pd.DataFrame(ledger_data)
ledger.to_csv('internal_ledger_jun.csv', index=False)

# 2. Load and Clean the Extracted PDF Bank Data (June)
bank = pd.read_csv('extracted_jun_statement.csv')

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

# 3. The Cross-Reference Engine
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
                'Audit_Flag': 'Amount Mismatch (Typo / Partial Payment)',
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

# 4. Sweep for missing bank charges
for b_idx, b_row in bank.iterrows():
    if b_idx not in matched_bank_indices:
        anomalies.append({
            'Audit_Flag': 'Missing in Ledger (Unrecorded Bank Charge)',
            'Ledger_Desc': 'N/A',
            'Bank_Desc': b_row['Description'],
            'Ledger_Amount': 0,
            'Bank_Amount': b_row['Net_Amount'],
            'Discrepancy': -b_row['Net_Amount']
        })

# 5. Export Executive Audit Report
print("📊 Compiling Final Audit Excel Report for June...")
with pd.ExcelWriter('audit_report_jun_2026.xlsx') as writer:
    pd.DataFrame(perfect_matches).to_excel(writer, sheet_name='Reconciled', index=False)
    pd.DataFrame(anomalies).to_excel(writer, sheet_name='Anomalies', index=False)

print("✅ Complete! Check your folder for 'audit_report_jun_2026.xlsx'.")