"""Evaluate on real SWF traces: many non-overlapping slices per log, rescaled to a target load.

    python -m experiments.run_real_trace  LOG.swf [LOG2.swf ...]  --slices 20 --jobs 300 --load 0.9

No tuning is done here: the settings are the ones chosen on synthetic dev seeds.
"""
import argparse
import os

import numpy as np
import pandas as pd

from experiments.run_experiments import paired_ci
from scheduler.compare import Settings, compare
from scheduler.loaders import WorkloadError, load_swf, offered_load, rescale_load

FIXED = ["FCFS", "SJF", "RR4"]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("logs", nargs="+")
    ap.add_argument("--slices", type=int, default=20)
    ap.add_argument("--jobs", type=int, default=300)
    ap.add_argument("--load", type=float, default=0.9)
    ap.add_argument("--check-factor", type=float, default=0.5,
                    help="controller checks every (factor x mean burst) ticks; real traces have huge "
                         "bursts, so the synthetic setting of 10 ticks would be far too frequent")
    ap.add_argument("--out", default="results_real")
    a = ap.parse_args()
    for path in a.logs:
        if not os.path.isfile(path):
            raise SystemExit(f"File not found: {path!r}\nRun this from the folder that contains the log, "
                             "or give the full path.")
    os.makedirs(a.out, exist_ok=True)

    rows = []
    ckpt = f"{a.out}/checkpoint.csv"
    if os.path.exists(ckpt):                      # resume: keep finished slices
        rows = pd.read_csv(ckpt).to_dict("records")
    done = {(r["log"], r["slice"]) for r in rows}
    for path in a.logs:
        name = os.path.basename(path)
        for k in range(a.slices):
            if (name, k) in done:
                continue
            try:
                jobs = load_swf(path, max_jobs=a.jobs, start=k * a.jobs)
            except WorkloadError:         # ran past the end of the log
                break
            if len(jobs) < a.jobs // 2:
                break
            jobs = rescale_load(jobs, a.load)
            interval = max(10, round(np.mean([j.burst for j in jobs]) * a.check_factor))
            for method, e in compare(jobs, Settings(check_interval=interval)).items():
                m = e.metrics()
                rows.append(dict(log=name, slice=k, method=method, load=offered_load(jobs),
                                 **{x: m[x] for x in ("avg_wait", "p95_wait", "max_wait",
                                                      "ctx_switches", "policy_switches")}))
            pd.DataFrame(rows).to_csv(ckpt, index=False)
            print(f"  {name} slice {k} done", flush=True)
        print("done", name, flush=True)
    if not rows:
        raise SystemExit("No usable slices were produced. Check --jobs/--slices and that the files are valid SWF logs.")
    df = pd.DataFrame(rows)
    best = df[df.method.isin(FIXED)].groupby(["log", "slice"]).avg_wait.min().rename("best_fixed")
    df = df.join(best, on=["log", "slice"])
    df["regret_pct"] = (df.avg_wait - df.best_fixed) / df.best_fixed * 100
    df.to_csv(f"{a.out}/real_runs.csv", index=False)

    out = [f"# Real-trace results\n\n{a.slices} slices x {a.jobs} jobs per log, arrivals rescaled to load {a.load}. "
           f"Controller check interval = {a.check_factor} x mean burst. No tuning on these logs.\n"]
    order = ["FCFS", "SJF", "RR4", "Rule router (old design)", "Shadow (adaptive)", "SJF* (cheats: true bursts)"]
    for log, d in df.groupby("log"):
        g = d.groupby("method").agg(slices=("slice", "nunique"), avg_wait=("avg_wait", "mean"),
                                    median_avg_wait=("avg_wait", "median"), p95_wait=("p95_wait", "mean"),
                                    max_wait=("max_wait", "mean"), rule_changes=("policy_switches", "mean"),
                                    mean_regret_pct=("regret_pct", "mean"),
                                    worst_slice_regret_pct=("regret_pct", "max")).loc[order]
        out.append(f"\n## {log}\n\n" + g.round(2).to_markdown() + "\n")
        pv = d.pivot(index="slice", columns="method", values="avg_wait")
        prow = []
        for base in FIXED + ["Rule router (old design)"]:
            mean, lo, hi, win = paired_ci(pv["Shadow (adaptive)"], pv[base])
            prow.append(dict(shadow_vs=base, mean_diff=round(mean, 1), ci=f"[{lo:.1f}, {hi:.1f}]",
                             shadow_wins=f"{win:.0%}",
                             verdict="shadow better" if hi < 0 else ("shadow worse" if lo > 0 else "no clear difference")))
        out.append("\nPaired comparison on avg wait (diff = Shadow - baseline, negative = Shadow better; "
                   "95% bootstrap CI over slices):\n\n" + pd.DataFrame(prow).to_markdown(index=False) + "\n")
    open(f"{a.out}/real_summary.md", "w").write("\n".join(out))
    print("\n".join(out))


if __name__ == "__main__":
    main()
