"""Command-line demo: python main.py   (no Streamlit needed)"""
import dataclasses
import pandas as pd
from config import DEFAULT_CONFIG
from data.workloads import BENCHMARK_WORKLOADS
from evaluation.runner import run_all

pd.set_option("display.width", 220)
pd.set_option("display.max_columns", 20)

if __name__ == "__main__":
    for objective in ("balanced", "responsive"):
        cfg = dataclasses.replace(DEFAULT_CONFIG, objective=objective)
        print(f"\n######## OBJECTIVE: {objective} ########")
        for name, workload in BENCHMARK_WORKLOADS.items():
            df, _, decision, sig = run_all(workload, cfg)
            print(f"\n=== {name} ===")
            print(f"Signature: avg_burst={sig['avg_burst']:.2f} cv={sig['burst_cv']:.2f} "
                  f"short_ratio={sig['short_burst_ratio']:.2f} density={sig['arrival_density']:.2f}")
            print(f"Class: {decision['label']}  ->  Policy: {decision['policy']}")
            print(f"Why:   {decision['reason']}")
            print(df.round(2).to_string(index=False))
