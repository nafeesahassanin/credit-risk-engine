"""
stress_simulator.py

Applied Monte Carlo macro stress scenarios to each company's 
financial metrics to simulate how their distress probability would chance
under adverse economic conditions. 
The macro scenarios simulate recession, rate shock, and sector crisis.
"""
# import modules
import sqlite3
import pandas as pd
import numpy as np
import os

# Configuration
DB_PATH = os.path.join(os.path.dirname(__file__), "database", "credit_risk.db")
TICKERS = ["BA", "F", "GE", "MMM", "CAT"]

NUM_SIMULATIONS = 10000
np.random.seed(42)

SCENARIOS = {
    "Recession": {
        "revenue_shock": {"mean": -0.20, "std": 0.05},
        "cost_shock": {"mean": 0.10, "std": 0.03},
        "asset_shock": {"mean": -0.10, "std": 0.03},
        "description": " 20% revenue decline, 10% cost increase"
    },
    "Rate Shock": {
        "revenue_shock": {"mean": -0.05, "std": 0.02},
        "cost_shock": {"mean": 0.15, "std": 0.04},
        "asset_shock": {"mean": -0.05, "std": 0.02},
        "description": " 5% revenue decline, 15% cost increase"
    },
    "Sector Crisis": {
        "revenue_shock": {"mean": -0.30, "std": 0.08},
        "cost_shock": {"mean": 0.05, "std": 0.02},
        "asset_shock": {"mean": -0.15, "std": 0.05},
        "description": " 30% revenue decline, 5% cost increase"
    }
}

def get_connection():
    return sqlite3.connect(DB_PATH)

def get_latest_financials():
    """
    Retrieves the most recent year's financial data for 
    each company from the database.
    """
    conn = get_connection()

    query = """
        SELECT
            i.ticker,
            i.year,
            i.revenue,
            i.ebit,
            i.net_income,
            b.total_assets,
            b.total_liabilities,
            b.working_capital,
            b.retained_earnings,
            b.shareholders_equity,
            b.current_assets,
            b.current_liabilities,
            m.market_cap,
            z.z_score,
            z.zone,
            cs.composite_score,
            cs.distress_probability
            FROM income_statement i
            JOIN balance_sheet b
                ON i.ticker = b.ticker
                AND i.year = b.year
            JOIN market_data m
                ON i.ticker = m.ticker
                AND i.year = m.year
            JOIN z_scores z
                ON i.ticker = z.ticker
                AND i.year = z.year
            JOIN composite_scores cs
                ON i.ticker = cs.ticker
                AND i.year = cs.year
            WHERE b.total_assets > 0
            GROUP BY i.ticker
            HAVING MAX(i.year)
            ORDER BY i.ticker
        """
    df = pd.read_sql_query(query,conn)
    conn.close()
    return df

def simulated_stressed_zscore(row,scenario, n_simulations):
    """
    Runs a Monte Carlo simulation of the Altman Z-Score 
    under a given stress scenario for one company.

    Paramters:
        row           : one company's financial data
        scenario      : dictionary of shcok parameters
        n_simulations : number of Monte Carlo draws

    Returns:
        numpy array of 10,000 simulated stressed Z-Scores
    """
    # Dram random shock from normal distributions
    revenue_shocks = np.random.normal(
        scenario["revenue_shock"]["mean"],
        scenario["revenue_shock"]["std"],
        n_simulations
        )
    cost_shocks = np.random.normal(
        scenario["cost_shock"]["mean"],
        scenario["cost_shock"]["std"],
        n_simulations
        )
    asset_shocks = np.random.normal(
        scenario["asset_shock"]["mean"],
        scenario["asset_shock"]["std"],
        n_simulations
        )
    
    # Apply shock to base financial metrics
    stressed_revenue = row["revenue"] * (1 + revenue_shocks)
    stressed_ebit = row["ebit"] * (1 + revenue_shocks) * (1 - cost_shocks)
    stressed_assets = row["total_assets"] * (1 + asset_shocks)
    stressed_working_capital = row["working_capital"] * (1 + revenue_shocks)

    # Recalculate Altman Z-Score with streesed metrics
    X1 = np.where(stressed_assets != 0, stressed_working_capital / stressed_assets, 0)
    X2 = np.where(stressed_assets != 0, row["retained_earnings"] / stressed_assets, 0)
    X3 = np.where(stressed_assets != 0, stressed_ebit / stressed_assets, 0)
    X4 = np.where(row["total_liabilities"] != 0, row["market_cap"] / row["total_liabilities"], 0)
    X5 = np.where(stressed_assets != 0, stressed_revenue / stressed_assets, 0)

    stressed_z_scores = (1.2*X1 + 1.4*X2 + 3.3*X3 + 0.6*X4 + 1.0*X5)
    return stressed_z_scores

def run_stress_scenarios():
    """
    Runs all the three stress scenarios for all five companies
    and compiles the results into a summary DataFram
    """
    df = get_latest_financials()
    results = []

    print("\n" + "=" *75)
    print("MONTE CARLO STRESS SIMULATION - 10,000 SCENARIOS EACH")
    print("=" * 75)

    for _, company in df.iterrows():
        ticker = company["ticker"]
        baseline_z = company["z_score"]
        baseline_prob = company["distress_probability"]

        print(f"\n{ticker} - Baseline Z-Score: "
              f"{baseline_z:.3f} | "
              f"Baseline Distress: {baseline_prob:.1f}%")
        print(f"{'Scenario':<20}{'Median Z':<12}"
              f"{'P5 Z':<12}{'P1 Z':<12}"
              f"{'Zone':<12}{'Change':<12}")
        print(" " + "-" * 68)
    
        for scenario_name, scenario_params in SCENARIOS.items():
            simulated_z_scores = simulated_stressed_zscore(
                company, scenario_params, NUM_SIMULATIONS)
            median_z = np.percentile(simulated_z_scores, 50)
            p5_z = np.percentile(simulated_z_scores, 5)
            p1_z = np.percentile(simulated_z_scores, 1)

            if median_z > 2.99:
                zone = "Safe"
            elif median_z > 1.81:
                zone = "Grey"
            else:
                zone = "Distress"
            
            z_change = median_z - baseline_z
            change_str = f"{z_change:+.3f}"

            print(f"{scenario_name:<20}"
                  f"{median_z:<12.3f}"
                  f"{p5_z:<12.3f}"
                  f"{p1_z:<12.3f}"
                  f"{zone:<12}"
                  f"{change_str:<12}")
            
            results.append({
                "ticker": ticker,
                "scenario": scenario_name,
                "baseline_z": baseline_z,
                "baseline_prob": baseline_prob,
                "median_z": median_z,
                "p5_z": p5_z,
                "p1_z": p1_z,
                "zone": zone,
                "z_change": z_change,
                "year": int(company["year"])
            })
    return pd.DataFrame(results)

def store_stress_results(df):
    """
    Stores stress simulation results in the database.
    """
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
                   CREATE TABLE IF NOT EXISTS stress_results(
                   ticker TEXT,
                   scenario TEXT, 
                   year INTEGER,
                   baseline_z REAL,
                   baseline_prob REAL,
                   median_z REAL,
                   p5_z REAL,
                   p1_z REAL,
                   zone TEXT,
                   z_change REAL,
                   PRIMARY KEY (ticker, scenario)
                   )
                   """)
    for row in df.itertuples(index=False):
        cursor.execute("""
                       INSERT OR REPLACE INTO stress_results
                       VALUES(?,?,?,?,?,?,?,?,?,?)
                       """, (row.ticker, row.scenario, row.year, row.baseline_z,
                             row.baseline_prob, row.median_z, row.p5_z, row.p1_z,
                             row.zone, row.z_change))
    conn.commit()
    conn.close()
    print("\nStress results stored in database successfully.")

def print_summary(df):
    """
    Prints a summary table showing which companies are most
    vulnerable to each stress scenario.
    """
    print("\n" + "=" *75)
    print("STRESS TEST VULNERABILITY SUMMARY")
    print("=" * 75)
    print("Most vulnerable companies per scenario (largest Z-Score decline): \n")

    for scenario in SCENARIOS.keys():
        scenario_data = df[df["scenario"] == scenario].copy()
        scenario_data = scenario_data.sort_values("z_change", ascending=True)

        print(f"{scenario}"
              f"{SCENARIOS[scenario]['description']}:")
        print(f"{'Company':<10}{'Baseline Z':<14}"
              f"{'Stressed Z':<14}{'Change':<12}{'Zone':<10}")
        print(" " + "-" *55)

        for _, row in scenario_data.iterrows():
            change_str = f"{row['z_change']:+.3f}"
            print(f"{row['ticker']:<10}"
                  f"{row['baseline_z']:<14.3f}"
                  f"{row['median_z']:<14.3f}"
                  f"{change_str:<12}"
                  f"{row['zone']:<10}")
        print()

    avg_change = df.groupby("ticker")["z_change"].mean()
    most_vulnerable = avg_change.idxmin()
    print(f"Most vulnerable across all scenarios: "
          f"{most_vulnerable} "
          f"(average Z-score change: {avg_change[most_vulnerable]:+.3f})")
    print()

if __name__ == "__main__":
    print("=" * 75)
    print("CREDIT RISK ENGINE - MONTE CARLO STRESS SIMULATION")
    print("=" *75)

    results_df = run_stress_scenarios()
    store_stress_results(results_df)
    print_summary(results_df)