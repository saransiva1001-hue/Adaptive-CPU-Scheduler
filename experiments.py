"""
Full evaluation. Run:  python experiments.py
Produces results/*.csv and results/*.png.
For every workload type: N seeded random workloads, all baselines + adaptive,
compared on every metric, plus 'regret' versus the best fixed policy.
"""
import os, dataclasses, statistics as st
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from config import DEFAULT_CONFIG
from data.workloads import generate_random_workload, WORKLOAD_TYPES
from evaluation.runner import run_all

OUT = "results"
N_RUNS, N_PROCS = 200, 10


def composite(row, cfg):
    """Score used only for regret analysis (lower = better).
    balanced  : wait + response + 0.5*max_wait      responsive: wait + 4*response + 0.5*max_wait"""
    w = 4.0 if cfg.objective == "responsive" else 1.0
    return row["avg_waiting_time"] + w * row["avg_response_time"] + 0.5 * row["max_waiting_time"]


def run_experiments(cfg=DEFAULT_CONFIG, n_runs=N_RUNS, n_procs=N_PROCS):
    rows, picks = [], []
    for wt in WORKLOAD_TYPES:
        for seed in range(n_runs):
            df, _, decision, _ = run_all(generate_random_workload(n_procs, wt, seed), cfg)
            df["adaptive"] = df["Algorithm"].str.startswith("Adaptive")
            df["Algorithm"] = df["Algorithm"].where(~df["adaptive"], "Adaptive")
            df["score"] = df.apply(lambda r: composite(r, cfg), axis=1)
            fixed = df[~df["adaptive"]]
            df["best_fixed_score"] = fixed["score"].min()
            df["workload"], df["seed"] = wt, seed
            rows.append(df)
            picks.append({"workload": wt, "seed": seed, "label": decision["label"], "policy": decision["policy"]})
    return pd.concat(rows, ignore_index=True), pd.DataFrame(picks)


def summarize(all_rows):
    cols = ["avg_waiting_time", "avg_turnaround_time", "avg_response_time", "max_waiting_time",
            "throughput", "context_switches", "starved_processes", "score"]
    return all_rows.groupby(["workload", "Algorithm"], sort=False)[cols].mean().round(2)


def plot_summary(summary):
    os.makedirs(OUT, exist_ok=True)
    for metric, title in [("avg_waiting_time", "Average Waiting Time"), ("avg_response_time", "Average Response Time"),
                          ("context_switches", "Context Switches"), ("score", "Composite Score (lower = better)")]:
        piv = summary[metric].unstack("Algorithm")
        ax = piv.plot(kind="bar", figsize=(11, 5), width=0.85)
        ax.set_title(f"{title} by workload type (mean of {N_RUNS} runs)")
        ax.set_ylabel(title); ax.set_xlabel(""); ax.grid(axis="y", linestyle="--", alpha=.6)
        plt.xticks(rotation=20); plt.tight_layout()
        plt.savefig(f"{OUT}/{metric}.png", dpi=130); plt.close()


def report(objective):
    global OUT
    cfg = dataclasses.replace(DEFAULT_CONFIG, objective=objective)
    OUT = f"results/{objective}"
    os.makedirs(OUT, exist_ok=True)
    print(f"\n{'#' * 20}  OBJECTIVE PROFILE: {objective.upper()}  {'#' * 20}")
    all_rows, picks = run_experiments(cfg)
    summary = summarize(all_rows)
    summary.to_csv(f"{OUT}/summary_by_workload.csv")
    all_rows.to_csv(f"{OUT}/raw_results.csv", index=False)
    plot_summary(summary)

    pd.set_option("display.width", 200)
    print(summary[["avg_waiting_time","avg_response_time","max_waiting_time","context_switches","starved_processes","score"]].to_string())

    print("\nPolicy chosen by the adaptive router (share of runs):")
    print(pd.crosstab(picks["workload"], picks["policy"], normalize="index").round(2).to_string())

    ad = all_rows[all_rows["Algorithm"] == "Adaptive"].copy()
    ad["regret_%"] = 100 * (ad["score"] - ad["best_fixed_score"]) / ad["best_fixed_score"]
    print("\nAdaptive regret vs best fixed policy per workload (0% = matched the best; lower = better):")
    print(ad.groupby("workload", sort=False)["regret_%"].mean().round(1).to_string())
    fixed = all_rows[all_rows["Algorithm"] != "Adaptive"]
    print("\nMean composite score over ALL workloads:")
    print(all_rows.groupby("Algorithm")["score"].mean().round(1).sort_values().to_string())


if __name__ == "__main__":
    for obj in ("balanced", "responsive"):
        report(obj)
