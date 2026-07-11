"""
visualizations.py

Creates all charts for the Credit Risk Engine project.

Charts produced:
1. Altman Z-Score timeline
2. Distress probabiltiy heatmap
3. Compoiste score radar chart
4. Stress test comparisom
5. Monte Carlo Distribution
"""

# import modules
import sqlite3
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import os

# Configuration
DB_PATH = os.path.join(os.path.dirname(__file__), "database", "credit_risk.db")
CHARTS_DIR = os.path.join(os.path.dirname(__file__), "charts")
TICKERS = ["BA", "F", "GE", "MMM", "CAT"]
COMPANY_NAMES = {
    "BA" : "Boeing",
    "F" : "Ford",
    "GE" : "GE",
    "MMM" : "3M",
    "CAT" : "Caterpillar"
}
COLORS = {
    "BA" : "mediumblue",
    "F" : "cadetblue",
    "GE" : "mediumpurple",
    "MMM" :"orangered",
    "CAT" : "darkorange"
}

def get_connection():
    return sqlite3.connect(DB_PATH)

def ensure_charts_dir():
    os.makedirs(CHARTS_DIR, exist_ok=True)

def save_chart(filename):
    """
    Saves the current matplotlib figure to the charts folder.
    """
    filepath = os.path.join(CHARTS_DIR, filename)
    plt.savefig(filepath, dpi=150, bbox_inches="tight")
    plt.show()
    plt.close()
    print(f"Saved: charts/{filename}")

# Chart 1: Z-Score Timeline
def plot_zscore_timeline():
    """
    Line chart shwoing each company's Altman Z-Score from 2021 to 2025.
    """
    conn = get_connection()
    df = pd.read_sql_query("""
                           SELECT ticker, year, z_score
                           FROM z_scores
                           ORDER BY ticker, year
                           """, conn)
    conn.close()

    fig, ax = plt.subplots(figsize=(12,7))

    for ticker in TICKERS:
        company = df[df["ticker"] == ticker]
        ax.plot(company["year"], company["z_score"],
                color = COLORS[ticker], linewidth=2.5,
                marker="o", markersize=6,
                label=COMPANY_NAMES[ticker])
        
        last = company.iloc[-1]
        ax.annotate(ticker,
                    xy=(last["year"], last["z_score"]),
                    xytext=(5,0),
                    textcoords = "offset points",
                    fontsize=9, color=COLORS[ticker],
                    fontweight="bold")
        
    ax.axhline(y=2.99, color="green", linewidth=1.5,
               linestyle="--", alpha=0.7, label="Safe threshold (2.99)")
    ax.axhline(y=1.81, color="red", linewidth=1.5,
               linestyle="--", alpha=0.7, label="Distress threshold (1.81)")
    ax.axhspan(2.99, ax.get_ylim()[1] if ax.get_ylim()[1]>3
               else 7, alpha=0.05, color="green")
    ax.axhspan(1.81, 2.99, alpha=0.05, color="yellow")
    ax.axhspan(0, 1.81, alpha=0.05, color="red")
    ax.set_title("Altman Z-Score Timeline - Manufacturing Companies (2021-2025)",
                 fontsize=13, fontweight="bold")
    ax.set_xlabel("Year", fontsize=10)
    ax.set_ylabel("Altman Z-Score", fontsize=10)
    ax.legend(fontsize=9, loc="upper left")
    ax.tick_params(axis="both", labelsize=9)
    ax.set_xticks(df["year"].unique())

    plt.tight_layout()
    save_chart("1_zscore_timeline.png")

# Chart 2: Distress Probability Heatmap
def plot_distress_heatmap():
    """
    Heatmap showing distress probability 
    for every company across every year.
    """
    conn = get_connection()
    df = pd.read_sql_query("""
                           SELECT ticker, year, distress_probability
                           FROM composite_scores
                           ORDER BY ticker, year
                           """, conn)
    conn.close()

    pivot = df.pivot(index="ticker", columns="year",
                     values="distress_probability")
    pivot = pivot.reindex(TICKERS)
    fig, ax = plt.subplots(figsize=(10,6))
    im = ax.imshow(pivot.values, cmap="RdYlGn_r",
                   aspect="auto", vmin=0, vmax=100)
    
    cbar = plt.colorbar(im, ax=ax)
    cbar.set_label("Distress Probability (%)", fontsize=10)

    ax.set_xticks(range(len(pivot.columns)))
    ax.set_xticklabels(pivot.columns.astype(int), fontsize=10)
    ax.set_yticks(range(len(pivot.index)))
    ax.set_yticklabels([COMPANY_NAMES[t] for t in pivot.index],
                       fontsize=10)
    
    for i in range(len(pivot.index)):
        for j in range(len(pivot.columns)):
            value = pivot.values[i,j]
            if not np.isnan(value):
                text_color = "white" if value > 60 else "black"
                ax.text(j, i, f"{value:.1f}%",
                        ha = "center", va="center",
                        fontsize=9, fontweight="bold",
                        color=text_color)

    ax.set_title("Distress Probability Heatmap - All Companies (2021-2025)",
                 fontsize=13, fontweight="bold")
    ax.set_xlabel("Year", fontsize=10)

    plt.tight_layout()
    save_chart("2_distress_heatmap.png")

# Chart 3: Composite Score Radar Chart
def plot_radar_chart():
    """
    Radar chart showing each company's scores across
    the four scoring categories for their most recent year.
    """      
    conn = get_connection()
    df = pd.read_sql_query("""
                           SELECT ticker, year, altman_score, profitability_score,
                           liquidity_score, efficiency_score
                           FROM composite_scores
                           ORDER BY ticker, year DESC
                           """, conn)
    conn.close()

    latest = df.groupby("ticker").first().reset_index()
    categories = ["Altman\nZ-Score", "Profitability", "Liquidity", "Efficiency"]
    n_categories= len(categories)
    
    angles = np.linspace(0, 2* np.pi, n_categories, endpoint=False).tolist()
    angles += angles[:1]
    fig, ax = plt.subplots(figsize=(10,8), subplot_kw=dict(polar=True))

    for _, row in latest.iterrows():
        ticker = row["ticker"]
        values = [
            row["altman_score"],
            row["profitability_score"],
            row["liquidity_score"],
            row["efficiency_score"]
                  ]
        values += values[:1]

        ax.plot(angles, values, color=COLORS[ticker],
                linewidth=2, label=COMPANY_NAMES[ticker])
        ax.fill(angles, values, color=COLORS[ticker], alpha=0.1)

    ax.set_xticks(angles[:-1])
    ax.set_xticklabels(categories, fontsize=10)
    ax.set_ylim(0,100)
    ax.set_yticks([20, 40, 60, 80, 100])
    ax.set_yticklabels(["20", "40", "60", "80", "100"],
                  fontsize=7)
    
    ax.set_title("Composite Score Radar Chart - Latest Year (2025)",
                 fontsize=13, fontweight="bold", pad=20)
    ax.legend(loc="upper right", bbox_to_anchor=(1.3, 1.1), 
              fontsize=9)
    
    plt.tight_layout()
    save_chart("3_radar_chart.png")

# Chart 4: Stress Test Comparison
def plot_stress_comparison():
    """
    Grouped bar chart comparing baseline Z-Score against
    stressed Z-Scores under each scenario for every company,
    """
    conn = get_connection()
    df = pd.read_sql_query("""
                           SELECT ticker, scenario, baseline_z, median_z, z_change
                           FROM stress_results
                           ORDER BY ticker, scenario
                        """, conn)
    conn.close()

    scenarios = df["scenario"].unique()
    x = np.arange(len(TICKERS))
    width = 0.2
    offsets = [-1.5, -0.5, 0.5, 1.5]
    fig, ax = plt.subplots(figsize = (14,7))

    baseline = df.groupby("ticker")["baseline_z"].first()
    ax.bar(x, [baseline[t] for t in TICKERS],
               width = 0.8, color = "lightgray", alpha=0.5, 
               label = "Baseline Z-Score", zorder=2)
    
    scenario_colors = ["steelblue", "darkorange", "crimson"]
    for i, (scenario, color) in enumerate(zip(scenarios, scenario_colors)):
        scenario_data = df[df["scenario"] == scenario]
        values = [scenario_data[scenario_data["ticker"]==t]
                 ["median_z"].values[0] for t in TICKERS]
        ax.bar(x + offsets[i+1] * width * 0.6, values,
               width=width, color=color, alpha=0.8,
               label=f"{scenario}", zorder=3)
        
    ax.axhline(y=2.99, color="green", linewidth=1.5,
               linestyle="--", alpha=0.7,
               label="Safe threshold (2.99)")
    ax.axhline(y=1.81, color="red", linewidth=1.5,
               linestyle="--", alpha=0.7,
               label="Distress threshold (1.81)")
    ax.set_title("Baseline vs Stressed Z-Scores - All Scenarios",
                 fontsize=13, fontweight="bold")
    ax.set_xlabel("Comapny", fontsize=10)
    ax.set_ylabel("Altman Z-Score", fontsize=10)
    ax.set_xticks(x)
    ax.set_xticklabels([COMPANY_NAMES[t] for t in TICKERS],
                       fontsize=10)
    ax.legend(fontsize=9)
    ax.tick_params(axis="y", labelsize=9)

    plt.tight_layout()
    save_chart("4_stress_comparison.png")

# Chart 5: Monte Carlo Distribution
def plot_monte_carlo_distribution():
    """
    Histogram showing the full distribution of 10,000 simulated
    Z-Scores for Boeing under the Sector Crisis scenario.
    """

    # import modules
    from stress_simulator import simulated_stressed_zscore
    from stress_simulator import SCENARIOS
    import sqlite3

    conn = get_connection()
    ba_data = pd.read_sql_query("""
        SELECT 
            i.ticker, i.year, i.revenue, i.ebit, i.net_income,
            b.total_assets, b.total_liabilities, b.working_capital,
            b.retained_earnings, b.shareholders_equity,
            b.current_assets, b.current_liabilities,
            m.market_cap, z.z_score
        FROM income_statement i
        JOIN balance_sheet b
            ON i.ticker = b.ticker AND i.year = b.year
        JOIN market_data m
            ON i.ticker = m.ticker AND i.year = m.year
        JOIN z_scores z
            ON i.ticker = z.ticker AND i.year = z.year
        WHERE i.ticker = 'BA'
        GROUP BY i.ticker
        HAVING MAX(i.year)
    """, conn)
    conn.close()

    ba_row = ba_data.iloc[0]
    scenario = SCENARIOS["Sector Crisis"]

    np.random.seed(42)
    simulated_z_scores = simulated_stressed_zscore(
        ba_row, scenario, 10000)
    fig, ax = plt.subplots(figsize=(12,6))
    ax.hist(simulated_z_scores, bins=60,
            color="steelblue", alpha=0.7,
            edgecolor="white", linewidth=0.5,
            density=True, label="Simulated Z-Scores")
    
    median_z = np.percentile(simulated_z_scores, 50)
    p5_z = np.percentile(simulated_z_scores, 5)
    p1_z = np.percentile(simulated_z_scores, 1)

    ax.axvline(x=ba_row["z_score"], color="black",
               linewidth=2, linestyle="-",
               label=f"Basline Z-Score: {ba_row['z_score']:.3f}")
    ax.axvline(x=median_z, color="green",
               linewidth=2, linestyle="--",
               label=f"Median Stressed: {median_z:.3f}")
    ax.axvline(x=p5_z, color="orange",
               linewidth=2, linestyle=":",
               label=f"P5 (5th Percentile): {p5_z:.3f}")
    ax.axvline(x=p1_z, color="red",
               linewidth=2, linestyle="-.",
               label=f"P1 (1st Percentile): {p1_z:.3f}")
    
    ax.axvspan(ax.get_xlim()[0], 1.81,
               alpha=0.1, color="red",
               label="Distress Zone (Z < 1.81)")
    ax.set_title("Boeing - Monte Carlo Z-Score Distribution\n"
                 "Sector Crsis Scenario (10,000 Simulations)",
                 fontsize=13, fontweight="bold")
    ax.set_xlabel("Simulated Altman Z-Score", fontsize=10)
    ax.set_ylabel("Density", fontsize=10)
    ax.legend(fontsize=9)
    ax.tick_params(axis="both", labelsize=9)

    plt.tight_layout()
    save_chart("5_monte_carlo_boeing.png")

if __name__ == "__main__":
    print("=" * 75)
    print("CREDIT RISK ENGINE - VISUALIZATIONS")
    print("=" * 75)

    ensure_charts_dir()

    print("\nGenerating charts...")
    plot_zscore_timeline()
    plot_distress_heatmap()
    plot_radar_chart()
    plot_stress_comparison()
    plot_monte_carlo_distribution()

    print("\n" + "=" * 75)
    print("All charts saved to charts/ folder")
    print("=" * 75)    
    
    
    