"""One place that runs every algorithm on a workload (used by app, experiments, tests)."""
import sys, os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import pandas as pd
from config import DEFAULT_CONFIG
from core.schedulers import fcfs, sjf, round_robin, priority_scheduling
from core.signature import calculate_workload_signature
from core.adaptive import adaptive_scheduler
from evaluation.metrics import calculate_metrics

METRIC_COLS = ["avg_waiting_time", "avg_turnaround_time", "avg_response_time", "max_waiting_time",
               "throughput", "context_switches", "starved_processes"]


def run_all(workload, cfg=DEFAULT_CONFIG):
    """Returns (DataFrame of metrics per algorithm, results dict, decision dict)."""
    c = cfg.context_switch_cost
    sig = calculate_workload_signature(workload, cfg)
    adaptive_res, decision = adaptive_scheduler(workload, sig, cfg)
    results = {
        "FCFS": fcfs(workload, c),
        "SJF": sjf(workload, c),
        f"Round Robin (q={cfg.fixed_rr_quantum})": round_robin(workload, cfg.fixed_rr_quantum, c),
        "Priority": priority_scheduling(workload, c),
        f"Adaptive -> {decision['policy']}": adaptive_res,
    }
    rows = []
    for name, res in results.items():
        m = calculate_metrics(res, cfg.starvation_overtakes)
        rows.append({"Algorithm": name, **{k: m[k] for k in METRIC_COLS}})
    return pd.DataFrame(rows), results, decision, sig
