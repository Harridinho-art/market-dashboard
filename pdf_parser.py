import pdfplumber
import pandas as pd
import os

def extract_statement_data(pdf_path):
    print(f"🔍 Initializing OCR & Extraction for: {pdf_path}")
    
    with pdfplumber.open(pdf_path) as pdf:
        # Target the first page
        page = pdf.pages[0]
        
        # Extract tables based on visual gridlines
        extracted_tables = page.extract_tables()
        
        if not extracted_tables:
            raise ValueError("No tables detected on the page.")
            
        # Isolate the main transaction table
        table_data = extracted_tables[0]
        
    # Separate headers from the raw data
    headers = table_data[0]
    transactions = table_data[1:]
    
    # Load into a Pandas DataFrame
    df = pd.DataFrame(transactions, columns=headers)
    
    # Clean up column names (strip hidden newline characters)
    df.columns = [str(col).replace('\n', ' ').strip() for col in df.columns]
    
    # Filter out any empty rows or accidental text captures
    df = df[df['Date'].notna() & (df['Date'].str.strip() != '')]
    
    return df

if __name__ == "__main__":
    print("🚀 Starting Batch Extraction Pipeline...\n" + "-"*40)
    
    # List of our target Q3 months
    months = ['Jun', 'Jul', 'Aug']
    
    for month in months:
        target_pdf = f"Corporate_Statement_{month}_2026.pdf"
        output_csv = f"extracted_{month.lower()}_statement.csv"
        
        if os.path.exists(target_pdf):
            try:
                # Run the extraction function
                df = extract_statement_data(target_pdf)
                
                # Save to CSV
                df.to_csv(output_csv, index=False)
                print(f"✅ Success! Extracted {len(df)} rows -> 💾 Saved to: {output_csv}\n")
                
            except Exception as e:
                print(f"❌ Pipeline Error on {target_pdf}: {e}\n")
        else:
            print(f"⚠️ File missing: {target_pdf}. Skipping...\n")
            
    print("-" * 40 + "\n🏁 Pipeline execution complete.")