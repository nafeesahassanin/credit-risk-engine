"""
data_ingestion.py

Pulls real financial data from five companies from Yahoo Finance 
and stores it in a SQLite database for use throughout the project

Companies analyzed:
- Boeing (BA)           
- Ford (F)              
- General Electric (GE) 
- 3M (MMM)       
- Caterpillar (CAT)       
"""

# import modules
import yfinance as yf
import pandas as pd
import sqlite3
import os


# configuration
TICKERS = ["BA", "F", "GE", "MMM", "CAT"] 
# path to SQLite database
DB_PATH = os.path.join(os.path.dirname(__file__), "database", "credit_risk.db")

def get_connection():
    """
    Creates and returns a connection to the SQLite database.
    """
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    return sqlite3.connect(DB_PATH)

def create_tables():
    """
    Creates the database tables if they do not already exist.
    """
    conn = get_connection()
    cursor = conn.cursor()
    
    # Income statement table
    cursor.execute("""
                   CREATE TABLE IF NOT EXISTS income_statement(
                   ticker TEXT, year INTEGER, revenue REAL,
                   gross_profit REAL, ebit REAL, net_income REAL, PRIMARY KEY (ticker,year)
                   )""")
    # Balance sheet table
    cursor.execute("""
                   CREATE TABLE IF NOT EXISTS balance_sheet(
                   ticker TEXT, year INTEGER, total_assets REAL, current_assets REAL,
                   current_liabilities REAL, total_liabilities REAL, retained_earnings REAL,
                   shareholders_equity REAL, working_capital REAL, PRIMARY KEY (ticker,year) )
                   """)
    # Cash flow table
    cursor.execute("""
                   CREATE TABLE IF NOT EXISTS cash_flow(
                   ticker TEXT, year INTEGER, operating_cash_flow REAL,
                   capital_expenditure REAL, free_cash_flow REAL, PRIMARY KEY (ticker, year))
                   """)
    # Market data table
    cursor.execute("""
                   CREATE TABLE IF NOT EXISTS market_data(
                   ticker TEXT, year INTEGER, market_cap REAL, PRIMARY KEY (ticker, year))
                   """)
    
    conn.commit()
    conn.close()
    print("Database tables created successfully.")

def safe_get(df, row_name):
    """
    Safely retrieves a row from a financial statement DataFrame.

    Parameters:
         df         : the financial statement DataFrame
         row_name   : the name of the row we want to retrieve
    Returns:
         The row as a pandas Series if found, or None if not found.
    """
    if row_name in df.index:
        return df.loc[row_name]
    
    return None

def safe_value(series, col):
    """
    Safely retrieves a single value from a pandas Series.
    
    Parameters: 
         series  : the row data
         col     : the column (year) 
    Returns:
         The numeric value, or 0.0 if missing/unavaible.
    """
    try:
        if series is None:
            return 0.0
        if col not in series.index:
            return 0.0
        val = series[col]

        if pd.isna(val):
            return 0.0
        return float(val)
    except Exception: 
        return 0.0
    
def pull_and_store_data():
    """
    Pulls financial data for all five companies
    from Yahoo Finance and stores it in the SQLite database.
    """
    conn = get_connection()
    cursor = conn.cursor()

    for ticker in TICKERS:
        print(f"\nPulling data for {ticker}...")
        
        try:
            stock = yf.Ticker(ticker)

            income_stmt = stock.financials
            balance_sht = stock.balance_sheet
            cash_flow = stock.cashflow
            info = stock.info
            market_cap = info.get("marketCap", 0)

            for col in income_stmt.columns:
                year = col.year
                
                # Income Statement
                revenue = safe_value(safe_get(income_stmt, "Total Revenue"),col)
                gross_profit = safe_value(safe_get(income_stmt, "Gross Profit"),col)
                ebit = safe_value(safe_get(income_stmt, "EBIT"), col)
                net_income = safe_value(safe_get(income_stmt, "Net Income"), col)
                cursor.execute("""
                               INSERT OR REPLACE INTO income_statement
                               VALUES (?,?,?,?,?,?)
                               """, (ticker, year, revenue, gross_profit, ebit, net_income))
                
                # Balance Sheet
                total_assets = safe_value(safe_get(balance_sht, "Total Assets"), col)
                current_assets = safe_value(safe_get(balance_sht, "Current Assets"), col)
                current_liabilities = safe_value(safe_get(balance_sht, "Current Liabilities"), col)
                total_liabilities = safe_value(safe_get(balance_sht, "Total Liabilities Net Minority Interest"), col)
                retained_earnings = safe_value(safe_get(balance_sht, "Retained Earnings"), col)
                shareholders_equity = safe_value(safe_get(balance_sht, "Stockholders Equity"), col)
                working_capital = current_assets - current_liabilities
                cursor.execute("""
                               INSERT OR REPLACE INTO balance_sheet
                               VALUES(?,?,?,?,?,?,?,?,?)
                               """, (ticker, year, total_assets, current_assets,
                                     current_liabilities, total_liabilities, retained_earnings,
                                     shareholders_equity, working_capital))
                
                # Cash FLow
                operating_cf = safe_value(safe_get(cash_flow, "Operating Cash Flow"), col)
                capex = safe_value(safe_get(cash_flow, "Capital Expenditure"), col)
                free_cash_flow = operating_cf - abs(capex)
                
                cursor.execute("""
                               INSERT OR REPLACE INTO cash_flow 
                               VALUES(?,?,?,?,?)
                               """, (ticker, year, operating_cf,
                                     capex, free_cash_flow))
                # Market Data
                cursor.execute("""
                               INSERT OR REPLACE INTO market_data
                               VALUES(?,?,?)
                               """, (ticker, year, market_cap))
            print(f" {ticker}: {len(income_stmt.columns)}"
                    f" years of data stored successfully")
            
        except Exception as e:
            print(f" Error pulling {ticker}: {e}")
            continue

    conn.commit()
    conn.close()
    print("\nAll data stored in database successfully.")

def verify_data():
    """
    Runs a quick SQL query to verify the data loaded correctly
    by printing a summary of what's in each table.
    """
    conn = get_connection()
    cursor = conn.cursor()
    print("\n----- DATABASE VERIFICATION -----")

    # Count row per ticker in income statement
    cursor.execute("""
                   SELECT ticker, COUNT(*) as years_of_data,
                   MIN(year) as earliest_year,
                   MAX(year) as latest_year
                   FROM income_statement
                   GROUP BY ticker
                   ORDER BY ticker
                   """)

    print("\nIncome Statement Coverage:")
    print(f" {'Ticker':<8}{'Years':<8}"
          f"{'From':<8}{'To':<8}")
    print(" "+"-"*32)
    for row in cursor.fetchall():
        print(f" {row[0]:<8}{row[1]:<8}{row[2]:<8}{row[3]:<8}")
    
    # Show a sample of the data for one company
    cursor.execute("""
                   SELECT ticker, year,
                   ROUND(revenue/1e9, 2) as revenue_billions,
                   ROUND(net_income/1e9, 2) as net_income_billions
                   FROM income_statement
                   WHERE ticker = 'BA'
                   ORDER BY year DESC
                   """)
    
    print("\nSample - Boeing Revenue and Net Income (billions):")
    print(f" {'Year':<8}{'Revenue':<15}{'Net Income':<15}")
    print(" "+"-"*38)
    for row in cursor.fetchall():
        print(f" {row[1]:<8}{row[2]:<14}{row[3]:<14}")
    
    conn.close()

if __name__ == "__main__":
    print("=="*55)
    print("CREDIT RISK ENGINE - DATA INGESTION")
    print("=="*55)
    create_tables()
    pull_and_store_data()
    verify_data()

    





