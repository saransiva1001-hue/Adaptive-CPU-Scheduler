"""Run every method on every workload over many random seeds and report honestly.

    python -m experiments.run_experiments --runs 60

Outputs (in ./results): runs.csv, summary.md, requirement.md, plots.
"""
import argparse
import os
import random
import time

import numpy as np
import pandas as pd

from scheduler.controllers import (FixedController, RuleController, Requirement,
                                   ShadowController)
from scheduler.engine import Engine
from scheduler.policies import FCFS, RoundRobin, SJF
from scheduler.workloads import WORKLOADS, generate

CS = 1                      # context-switch cost in ticks
SWITCH_PENALTY = 1          # extra ticks charged when the controller changes rule
CHECK = 10                  # controller looks at the system every 10 ticks
FIXED = ["FCFS", "SJF", "RR4"]            # the realistic fixed pool (also the candidates)


def pool():
    return [FCFS(), SJF(), RoundRobin(4)]


def make_methods(requirement=None):
    f, s, r = pool()

    def shadow(**kw):                      # settings chosen on dev seeds (see tune_on_dev_seeds.py)
        c = pool()
        return ShadowController(c, initial=c[1], **kw)      # start on SJF

    m = {
        "FCFS": lambda: FixedController(f),
        "SJF": lambda: FixedController(s),
        "RR4": lambda: FixedController(r),
        "SJF* (cheats: true bursts)": lambda: FixedController(SJF(use_true=True)),
        "Rule router (old design)": lambda: RuleController(f, s),
        "Shadow (A)": lambda: shadow(),
        "Shadow+Guard (A+B)": lambda: shadow(guard=True),
    }
    if requirement is not None:
        m["Shadow+Req (A+C)"] = lambda: shadow(requirement=requirement)
    return m


def run_one(jobs, controller):
    t0 = time.perf_counter()
    e = Engine(jobs, controller, cs_cost=CS, switch_penalty=SWITCH_PENALTY,
               check_interval=CHECK).run()
    m = e.metrics()
    m["wall_ms"] = (time.perf_counter() - t0) * 1000
    return m


def paired_ci(a, b, n_boot=2000, seed=0):
    """Bootstrap 95% CI of mean(a - b) for paired samples, plus win-rate of a over b."""
    d = np.asarray(a) - np.asarray(b)
    rng = np.random.default_rng(seed)
    boots = rng.choice(d, size=(n_boot, len(d)), replace=True).mean(axis=1)
    return d.mean(), np.percentile(boots, 2.5), np.percentile(boots, 97.5), float((d < 0).mean())


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--runs", type=int, default=60)
    ap.add_argument("--out", default="results")
    args = ap.parse_args()
    os.makedirs(args.out, exist_ok=True)

    rows = []
    methods = make_methods()
    for w in WORKLOADS:
        for seed in range(args.runs):
            jobs = generate(w, seed)
            for name, mk in methods.items():
                m = run_one(jobs, mk())
                m.update(workload=w, seed=seed, method=name)
                rows.append(m)
        print(f"done {w}")
    df = pd.DataFrame(rows)

    # hindsight-best fixed rule per (workload, seed): what an all-knowing chooser of ONE rule gets
    fx = df[df.method.isin(FIXED)].groupby(["workload", "seed"]).avg_wait.min().rename("best_fixed")
    df = df.join(fx, on=["workload", "seed"])
    df["regret_pct"] = (df.avg_wait - df.best_fixed) / df.best_fixed * 100
    df.to_csv(f"{args.out}/runs.csv", index=False)

    # ---------- summary table --------------------------------------------------
    lines = ["# Results\n", f"{args.runs} random seeds per workload. Context switch = {CS} tick, "
             f"rule-change penalty = {SWITCH_PENALTY} tick.\n",
             "Regret = % worse than the best single fixed rule chosen in hindsight "
             "(negative = better than any single fixed rule).\n"]
    order = list(methods.keys())
    for w in WORKLOADS:
        d = df[df.workload == w]
        g = d.groupby("method").agg(avg_wait=("avg_wait", "mean"), p95_wait=("p95_wait", "mean"),
                                    max_wait=("max_wait", "mean"), ctx=("ctx_switches", "mean"),
                                    rule_changes=("policy_switches", "mean"),
                                    regret_pct=("regret_pct", "mean")).loc[order]
        lines.append(f"\n## {w}\n\n" + g.round(2).to_markdown() + "\n")

    # ---------- paired comparison of adaptive methods vs fixed rules -----------------
    lines.append("\n## Paired comparison (avg wait, lower is better)\n")
    lines.append("diff = adaptive - baseline (negative = adaptive better). CI = 95% bootstrap.\n")
    rows2 = []
    for w in WORKLOADS:
        d = df[df.workload == w].pivot(index="seed", columns="method", values="avg_wait")
        for adaptive in ["Shadow (A)", "Shadow+Guard (A+B)", "Rule router (old design)"]:
            for base in ["FCFS", "SJF", "RR4"]:
                mean, lo, hi, win = paired_ci(d[adaptive], d[base])
                verdict = "better" if hi < 0 else ("worse" if lo > 0 else "no clear difference")
                rows2.append(dict(workload=w, adaptive=adaptive, baseline=base,
                                  diff=round(mean, 2), ci=f"[{lo:.2f}, {hi:.2f}]",
                                  win_rate=f"{win:.0%}", verdict=verdict))
    lines.append(pd.DataFrame(rows2).to_markdown(index=False) + "\n")

    # ---------- overhead ------------------------------------------------------------
    ov = df.groupby("method").agg(controller_ms_per_run=("controller_ms", "mean"),
                                  wall_ms_per_run=("wall_ms", "mean")).loc[order]
    lines.append("\n## Overhead (wall-clock, this machine)\n\n" + ov.round(2).to_markdown() + "\n")
    open(f"{args.out}/summary.md", "w").write("\n".join(lines))

    # ---------- Idea C: requirement experiment --------------------------------------
    req_lines = ["# Requirement experiment (Idea C)\n",
                 "Target: p95 waiting time <= LIMIT, where LIMIT = 1.25 x the mean of the best fixed "
                 "rule's p95 (a tight but reachable target). 'Violation rate' = share of runs whose "
                 "ACTUAL p95 over the whole run broke the limit.\n"]
    req_rows = []
    for w in WORKLOADS:
        d = df[df.workload == w]
        best_p95 = d[d.method.isin(FIXED)].groupby("seed").p95_wait.min().mean()
        limit = 1.25 * best_p95
        req = Requirement("p95_wait", limit)
        extra = make_methods(req)["Shadow+Req (A+C)"]
        for seed in range(args.runs):
            m = run_one(generate(w, seed), extra())
            req_rows.append(dict(workload=w, seed=seed, method="Shadow+Req (A+C)",
                                 avg_wait=m["avg_wait"], p95_wait=m["p95_wait"], limit=limit))
        for name in ["FCFS", "SJF", "RR4", "Shadow+Guard (A+B)"]:
            dd = d[d.method == name]
            for _, r in dd.iterrows():
                req_rows.append(dict(workload=w, seed=int(r.seed), method=name,
                                     avg_wait=r.avg_wait, p95_wait=r.p95_wait, limit=limit))
    rq = pd.DataFrame(req_rows)
    rq["violated"] = rq.p95_wait > rq.limit
    t = rq.groupby(["workload", "method"]).agg(limit=("limit", "first"),
                                               violation_rate=("violated", "mean"),
                                               avg_wait=("avg_wait", "mean"),
                                               p95_wait=("p95_wait", "mean")).round(2)
    req_lines.append(t.to_markdown() + "\n")
    open(f"{args.out}/requirement.md", "w").write("\n".join(req_lines))

    # ---------- plots ---------------------------------------------------------------
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    show = ["FCFS", "SJF", "RR4", "Rule router (old design)", "Shadow (A)", "Shadow+Guard (A+B)"]
    piv = df.groupby(["workload", "method"]).avg_wait.mean().unstack().loc[list(WORKLOADS), show]
    ax = piv.plot(kind="bar", figsize=(11, 5))
    ax.set_ylabel("average waiting time (ticks, lower is better)")
    ax.set_title("Average wait by workload")
    plt.xticks(rotation=20)
    plt.tight_layout()
    plt.savefig(f"{args.out}/avg_wait.png", dpi=140)
    plt.close()

    rg = df.groupby(["workload", "method"]).regret_pct.mean().unstack().loc[list(WORKLOADS), show]
    ax = rg.plot(kind="bar", figsize=(11, 5))
    ax.axhline(0, color="k", lw=0.8)
    ax.set_ylabel("regret vs best single fixed rule in hindsight (%)")
    ax.set_title("Regret (negative = beats every single fixed rule)")
    plt.xticks(rotation=20)
    plt.tight_layout()
    plt.savefig(f"{args.out}/regret.png", dpi=140)
    plt.close()
    print(f"\nWrote results to ./{args.out}/")


if __name__ == "__main__":
    main()
