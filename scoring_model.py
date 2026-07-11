"""
scoring_model.py

Extends the Altman Z-Score with additional finanical metrics
and converts the combined score into a probability of financial distress.
"""

# import modules
import sqlite3
import pandas as pd
import numpy as np
import os

# Configuration
DB_PATH = os.path.join(os.path.dirname(__file__),
                       "database", "credit_risk.db")
TICKERS = ["BA", "F", "GE", "MMM", "CAT"]

WEIGHTS = {
    "altman": 0.40,
    "profitability": 0.35,
    "liquidity": 0.20,
    "efficiency": 0.15
}

def get_connection():
    return sqlite3.connect(DB_PATH)

def calculate_extended_metrics():
    """
    Returns a DataFrame with one row per company 
    per year containing all extended metrics.
    """
    conn = get_connection()

    query = """
        SELECT
            i. ticker,
            i.year,
            
            -- Profitability metrics
            CASE WHEN i.revenue != 0
                THEN i.net_income / i.revenue
                ELSE 0 END AS net_profit_margin,
            
            -- Return on Assets
            CASE WHEN b.total_assets != 0
                THEN i.net_income / b.total_assets
                ELSE 0 END AS return_on_assets,

            -- Liquidity metrics
            CASE WHEN b.current_liabilities != 0
                THEN b.current_assets / b.current_liabilities
                ELSE 0 END AS current_ratio,
            
            -- Free Cash Flow Margin
            CASE WHEN i.revenue != 0
                THEN c.free_cash_flow / i.revenue
                ELSE 0 END AS fcf_margin,

            -- Efficiency metris
            CASE WHEN b.total_assets != 0
                THEN i.revenue / b.total_assets
                ELSE 0 END AS asset_turnover,

            -- Debt to Equity
            CASE WHEN b.shareholders_equity != 0
                THEN b.total_liabilities / b.shareholders_equity
                ELSE 0 END AS debt_to_equity,
            
            -- Raw values needed for scoring
            i.revenue,
            i.net_income,
            b.total_assets,
            b.total_liabilities,
            b.shareholders_equity,
            c.free_cash_flow,
            z.z_score,
            z.zone

        FROM income_statement i
        JOIN balance_sheet b
            ON i.ticker = b.ticker
            AND i.year = b.year
        JOIN cash_flow c
            ON i.ticker = b.ticker
            AND i.year = c.year
        JOIN z_scores z
            ON i.ticker = z.ticker
            AND i.year = z.year
        WHERE b.total_assets > 0
        GROUP BY i.ticker, i.year
        ORDER BY i.ticker, i.year DESC
    """
    df = pd.read_sql_query(query,conn)
    conn.close()
    return df

def normalize_score(series, higher_is_better=True):
    """
    Normalizes a series of values to a 0-100 scale 
    so that different metrics can be combined into one composite score.

    Parameters:
        series:            pandas Series of values to normalize
        higher_is_better:  if True, higher values get higher scores
                           if False, higher values get lower scores

    Returns:
        pandas Series of scores from 0 to 100
    """
    min_val = series.min()
    max_val = series.max()

    if max_val == min_val:
        return pd.Series([50.0] * len(series),
                         index=series.index)
    
    normalized = (series - min_val) / (max_val - min_val) *100

    if not higher_is_better:
        normalized = 100 - normalized
    
    return normalized

def calculate_composite_scores(df):
    """
    Combines the Altman Z-Score with extended metrics into a single
    composite financial health score from 0-100,
    then converts that score to a distress probability.
    """

    df["altman_score"] = normalize_score(df["z_score"], higher_is_better=True)
    df["profitability_score"] = (
        normalize_score(df["net_profit_margin"],
                        higher_is_better=True) * 0.5 + 
        normalize_score(df["return_on_assets"], higher_is_better=True) *0.5
    )
    df["liquidity_score"] = (
        normalize_score(df["current_ratio"], higher_is_better=True) * 0.5 +
        normalize_score(df["fcf_margin"], higher_is_better=True) *0.5
    )
    df["efficiency_score"]=(
        normalize_score(df["asset_turnover"], higher_is_better=True) * 0.6 +
        normalize_score(df["debt_to_equity"], higher_is_better=False * 0.4)
    )
    
    # Calculate weighted composite score
    df["composite_score"] = (
            WEIGHTS["altman"] * df["altman_score"] +
            WEIGHTS["profitability"] * df["profitability_score"] +
            WEIGHTS["liquidity"] * df["liquidity_score"] +
            WEIGHTS["efficiency"] * df["efficiency_score"]
    )

    # Convert to distress probability
    k = 0.1
    midpoint = 50

    df["distress_probability"] = (
        1/ (1 + np.exp(k * (df["composite_score"]- midpoint)))
    ) * 100
    
    return df

def store_composite_scores(df):
    """
    Stores the composite scores and distress probabilities back into the database
    """
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
                   CREATE TABLE IF NOT EXISTS composite_scores(
                   ticker TEXT,
                   year INTEGER,
                   altman_score REAL,
                   profitability_score REAL,
                   liquidity_score REAL,
                   efficiency_score REAL,
                   composite_score REAL,
                   distress_probability REAL,
                   PRIMARY KEY (ticker, year)
                   )
                   """)
    
    for row in df.itertuples(index=False):
        cursor.execute("""
                       INSERT OR REPLACE INTO composite_scores
                       VALUES (?,?,?,?,?,?,?,?)
                    """, (row.ticker, row.year, row.altman_score,
                          row.profitability_score, row.liquidity_score,
                          row.efficiency_score, row.composite_score, row.distress_probability))
    conn.commit()
    conn.close()
    print("Composite scores stored in database successfully.")

def print_results(df):
    """
    Prints the composite scores and distress probabilities
    in a formatted table.
    """
    print("\n" + "=" *75)
    print("EXTENDED SCORING MODEL - COMPOSITE SCORES AND DISTRESS PROBABILITY")
    print("=" * 75)
    print(f"{'Ticker':<8}{'Year':<8}{'Altman':<10}{'Profit':<10}"
          f"{'Liquid':<10}{'Effic':<10}{'Composite':<12}{'Distress %':<12}")
    print(" " + "-" *70)

    for ticker in TICKERS:
        company_data = df[df["ticker"]== ticker]
        for _, row in company_data.iterrows():
            dist_str = f"{row['distress_probability']:.1f}%"
            print(f"{row['ticker']:<8}{int(row['year']):<8}"
                  f"{row['altman_score']:<10.1f}"
                  f"{row['profitability_score']:<10.1f}"
                  f"{row['liquidity_score']:<10.1f}"
                  f"{row['efficiency_score']:<10.1f}"
                  f"{row['composite_score']:<10.1f}"
                  f"{dist_str:<12}")
        print()
    print("=" *75)

def print_summary(df):
    """
    Prints the most recent year summary ranked by
    distress probability from highest to lowest risk.
    """
    print("\n-----DISTRESS PROBABILITY RANKING (Latest Year)-----")
    print(f"{'Rank':<6}{'Company':<10}{'Zone':<15}"
          f"{'Composite':<12}{'Distress %':<12}{'Assessment':<15}")
    print(" " + "-" * 65)

    latest = df.sort_values("year", ascending=False).groupby("ticker").first().reset_index()
    latest = latest.sort_values("distress_probability", ascending=False)

    for rank, (_,row) in enumerate(latest.iterrows(),1):
        prob = row["distress_probability"]
        if prob >= 70:
            assessment = "High Risk"
        elif prob >= 40:
            assessment = "Moderate Risk"
        else: 
            assessment = "Low Risk"
        
        dist_str = f"{prob:.1f}%"
        comp_str = f"{row['composite_score']:.1f}"

        print(f"{rank:<6}{row['ticker']:<10}"
              f"{row['zone']:<15}"
              f"{comp_str:<12}"
              f"{dist_str:<12}"
              f"{assessment:<15}")
    print()


if __name__ == "__main__":
    print("=" * 75)
    print("CREDIT RISK ENGINE - EXTENDED SCORING MODEL")
    print("=" * 75)

    df = calculate_extended_metrics()
    df = calculate_composite_scores(df)
    store_composite_scores(df)
    print_results(df)
    print_summary(df)