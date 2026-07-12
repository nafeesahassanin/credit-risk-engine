"""
main.py

Runs the complete Credit Risk Engine pipeline in sequence.
Pipeline:
    1. Data Ingestion
    2. Altman Z-Score
    3. Scoring Model
    4. Stress Simulator
    5. Visualizations
"""
# import modules
import time
import os

from data_ingestion import (create_tables, pull_and_store_data, verify_data)
from altman_zscore import (calculate_z_scores, store_z_scores, print_results, print_summary)
from scoring_model import (calculate_extended_metrics, calculate_composite_scores, store_composite_scores)
from stress_simulator import (run_stress_scenarios, store_stress_results)
from visualizations import (ensure_charts_dir, plot_zscore_timeline, plot_distress_heatmap, plot_radar_chart, 
                            plot_stress_comparison, plot_monte_carlo_distribution)

from scoring_model import print_summary as scoring_summary
from stress_simulator import print_summary as stress_summary

def print_header(title):
    """Prints a clean section header to seperate pipeline stages."""
    print("\n"+"="*75)
    print(f" {title}")
    print("="*75)

def run_pipeline():
    """
    Executes the complete credit risk analysis pipeline
    from raw data ingestion through visualization.
    """
    start_time = time.time()

    print("\n"+"="*75)
    print(" PREDICTIVE CREDIT RISK ENGINE")
    print(" Manufacturing Sector Analysis - BA, F, GE, MMM, CAT")
    print(" 2021-2025 | Altman Z-Score + Monte Carlo Stress Testing")
    print("="*75)

    # Stage 1: Data Ingestion
    print_header("STAGE 1: DATA INGESTION")
    create_tables()
    pull_and_store_data()
    verify_data()

    # Stage 2: Altman Z-Score
    print_header("STAGE 2: ALTMAN Z-SCORE CALCULATION")
    z_score_df = calculate_z_scores()
    store_z_scores(z_score_df)
    print_results(z_score_df)
    print_summary(z_score_df)

    # Stage 3: Extended Scoring Model
    print_header("STAGE 3: EXTENDED SCORING MODEL")
    scoring_df = calculate_extended_metrics()
    scoring_df = calculate_composite_scores(scoring_df)
    store_composite_scores(scoring_df)
    scoring_summary(scoring_df)

    # Stage 4: Monte Carlo Stress Simulation
    print_header("STAGE 4: MONTE CARLO STRESS SIMULATION")
    stress_df = run_stress_scenarios()
    store_stress_results(stress_df)
    stress_summary(stress_df)

    # Stage 5: Visualizations
    print_header("STAGE 5: GENERATING VISUALIZATIONS")
    ensure_charts_dir()
    plot_zscore_timeline()
    plot_distress_heatmap()
    plot_radar_chart()
    plot_stress_comparison()
    plot_monte_carlo_distribution()

    # Final Summary
    end_time = time.time()
    runtime = end_time - start_time

    print("\n"+"="*75)
    print(" PIPELINE COMPLETE")
    print("="*75)
    print(f"\n Total runtime: {runtime:.2f} seconds")
    print(f" Database: database/credit_risk.db")
    print(f" Charts: charts/(5 files)")
    print(f"\n Key Findings:")
    print(f" - Ford and Boeing classified as High Risk")
    print(f"   (distress probabilities: 81.6% and 71.5%)")
    print(f" - GE shows recovery: Grey Zone in 2022-2023,")
    print(f"   Safe Zone in 2024-2025")
    print(f" - Boeing most vulnerable under stress")
    print(f"   (average Z-Score change: -0.06 across all scenarios)")
    print(f" - Caterpillar benchmark healthy manufacturer")
    print(f"   (distress probability: 1.7%, Safe across all stress)")
    print(f" - 3M 2023 distress event (89.9% probability)")
    print(f"   captured by model - driven by PFAS litigation")
    print()

# Run pipeline
if __name__ == "__main__":
    run_pipeline()
