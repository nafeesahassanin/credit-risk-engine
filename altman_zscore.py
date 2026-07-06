"""
altman_zscore.py

Implements the Altman Z-Score model for predicting corportate 
financial distress across five manufacturing companies.

Z-Score Interpretation:
    Z > 2.99          : Safe Zone      -Low risk of bankruptcy
    1.81 < Z < 2.99   : Grey Zone      -Moderate risk of bankruptcy
    Z < 1.81          : Distress Zone  -High risk of bankruptcy
"""
 # import modules
import sqlite3
import pandas as pd
import numpy as np
import os

# Configuration
DB_PATH = os.path.join(os.path.dirname(__file__), "database", "credit_risk.db")
TICKERS = ["BA", "F", "GE", "MMM", "CAT"]

# Coefficients
COEFFICIENTS = {
    "X1": 1.2, # Working Capital / Total Assets
    "X2": 1.4, # Retained Earnings / Total Assets
    "X3": 3.3, # EBIT / Total Assets
    "X4": 0.6, # Market Value of Equity / Total Liabilities
    "X5": 1.0  # Sales / Total Assets
}
# Z-Score threshold boundaries
SAFE_ZONE = 2.99
DISTRESS_ZONE = 1.81

def get_connection():
    """
    Opens and returns a database connection
    """
    return sqlite3.connect(DB_PATH)

def calculate_z_scores():
    """
    Calculates the Altman Z-Score for each company for each year of avaiable data

    X1 - Liquidity
    X2 - Profitability
    X3 - Earnings Power
    X4 - Leverage
    X5 - Asset Efficiency

    Returns:
        A pandas DataFrame with columns:
        ticker, year, X1, X2, X3, X4, X5, z_score, zone
    """
    conn = get_connection()
    
    # SQL query to join all four tables together for the Z-Score calculation
    query = """
    SELECT
        i. ticker,
        i. year,
        -- X1: Working Capital / Total Assets
        CASE WHEN b.total_assets != 0
            THEN b.working_capital / b.total_assets
            ELSE 0 END AS X1,

        -- X2: Retained Earnings / Total Assets
        CASE WHEN b.total_assets != 0
            THEN b.retained_earnings / b.total_assets
            ELSE 0 END AS X2,

        -- X3: EBIT / Total Assets
        CASE WHEN b. total_assets != 0 
            THEN i.ebit/ b.total_assets
            ELSE 0 END AS X3,
        
        -- X4: Market Cap / TOtal Liabilities
        CASE WHEN b.total_liabilities != 0
            THEN m.market_cap / b.total_liabilities
            ELSE 0 END AS X4,

        -- X5: Revenue / Total Assets
        CASE WHEN b.total_assets != 0
            THEN i.revenue / b.total_assets
            ELSE 0 END AS X5
    
    FROM income_statement i
    JOIN balance_sheet b
        ON i.ticker = b.ticker
        AND i.year = b.year
    JOIN market_data m
        ON i.ticker = m.ticker
        AND i.year = m.year
    WHERE b.total_assets > 0
    ORDER BY i.ticker, i.year DESC
    """

    # run the query and load the results into a pandas DataFrame
    df = pd.read_sql_query(query, conn)
    conn.close()

    # Calculate Z-Score using Altman Z-Score formula
    df["z_score"] = (
        COEFFICIENTS["X1"] * df["X1"] +
        COEFFICIENTS["X2"] * df["X2"] +
        COEFFICIENTS["X3"] * df["X3"] +
        COEFFICIENTS["X4"] * df["X4"] +
        COEFFICIENTS["X5"] * df["X5"])
    # Assign Zone Labels
    df["zone"] = np.where(
        df["z_score"] > SAFE_ZONE, "Safe",
        np.where(
            df["z_score"] > DISTRESS_ZONE, "Grey", 
        "Distress"
        )
    )
    return df

def store_z_scores(df):
    """
    Store the calculated Z-Scores back into the database 
    so other files can access them without recalculating
    """
    conn = get_connection()
    cursor = conn.cursor()

    # Create a table for Z-Score results
    cursor.execute("""
                   CREATE TABLE IF NOT EXISTS z_scores (
                   ticker TEXT,
                   year INTEGER,
                   X1 REAL,
                   X2 REAL,
                   X3 REAL,
                   X4 REAL,
                   X5 REAL,
                   z_score REAL,
                   zone TEXT,
                   PRIMARY KEY (ticker, year)
                   )
                """)
    
    # Insert each row the DataFrame into the database
    for row in df.itertuples(index=False):
        cursor.execute("""
                       INSERT OR REPLACE INTO z_scores
                       VALUES (?,?,?,?,?,?,?,?,?)
                       """, (row.ticker, row.year, row.X1, row.X2,
                             row.X3, row.X4, row.X5, row.z_score, row.zone))
    conn.commit()
    conn.close()
    print("Z-Scores stored in database successfully.")

def print_results(df):
    """
    Prints a formatted table to Z-Score results
    """
    print("\n" + "="*75)
    print("ALTMAN Z-SCORE RESULTS - MANUFACTURING COMPANIES (2021-2025)")
    print("=" * 75)
    print(f" Zones: Safe (Z > 2.99) | Grey (1.81 - 2.99) | Distress (Z < 1.81)")
    print("=" * 75)
    
    # Loop through each company
    for ticker in TICKERS:
        company_data = df[df["ticker"] == ticker]

        if company_data.empty:
            print(f"\n {ticker}: No data available")
            continue
        
        print(f"\n {ticker}")
        print(f"{'Year':<8}{'X1':<8}{'X2':<8}{'X3':<8}{'X4':<8}{'X5':<8}{'Z-Score':<10}{'Zone':<12}")
        print(" " + "-" * 68)
    
        for _, row in company_data.iterrows():
            if row["zone"] == "Safe":
                zone_display = "Safe"
            elif row["zone"] == "Grey":
                zone_display = "Grey"
            else:
                zone_display = "Distress"

            print(f"{int(row['year']):<8}"
                  f"{row['X1']:>6.3f} "
                  f"{row['X2']:>6.3f} "
                  f"{row['X3']:>6.3f} "
                  f"{row['X4']:>6.3f} "
                  f"{row['X5']:>6.3f} "
                  f"{row['z_score']:>10.3f} "
                  f"{zone_display:>8}")
    print("\n" + "=" * 75)

def print_summary(df):
    """
    Prints a summary showing which companies are in which zone in their most recent year,
    and flags any companies that have been deteriorating over time
    """
    print("\n----- LATEST YEAR SUMMARY -----")
    print(f" {'Company':<10}{'Year':<8}{'Z-Score':<12}{'Zone':<12}"
          f"{'Trend':<10}")
    print(" " + "-" * 55)

    for ticker in TICKERS:
        company_data = df[df["ticker"] == ticker].sort_values(
            "year", ascending=False)
        
        if company_data.empty:
            continue

        latest = company_data.iloc[0]
        latest_score = latest["z_score"]
        latest_zone = latest["zone"]
        latest_year = int(latest["year"])

        # Calculate trend
        if len(company_data) > 1: 
            previous_score = company_data.iloc[1]["z_score"]
            change = latest_score - previous_score
            if change > 0.1:
                trend = "Improving"
            elif change < -0.1:
                trend = "Declining"
            else:
                trend = "Stable"
        else:
            trend = "N/A"
        
        print(f" {ticker:<8}{latest_year:<8}"
              f"{latest_score:<12.3f}{latest_zone:<12}"
              f"{trend}")
    print()

if __name__ == "__main__":
    print("==" * 75)
    print("CREDIT RISK ENGINE - ALTMAN Z-SCORE CALCULATION")
    print("=" * 75)

    df = calculate_z_scores()
    store_z_scores(df)
    print_results(df)
    print_summary(df)
