"""Does using the user-requested runtime (SWF field 9) give better burst guesses and better scheduling?

    python -m experiments.run_estimator_study LOG.swf[.gz] --slices 30 --jobs 200 --load 0.9

Compares three ways to guess a job's length at arrival:
  history    - per-user running average of past jobs (the original method)
  requested  - the runtime the user asked for
  corrected  - requested time x the user's learned (actual / requested) ratio
Only logs that contain requested times can show a difference (the Paragon log has none).
Saves progress after every slice, so an interrupted run can simply be restarted.
"""
import argparse
import os

import numpy as np
import pandas as pd

from experiments.run_experiments import paired_ci
from scheduler.compare import Settings, compare
from scheduler.loaders import WorkloadError, load_swf, offered_load, rescale_load

MODES = ["history", "requested", "corrected"]
NEEDED_FILES = ["scheduler/job.py", "scheduler/estimator.py", "scheduler/engine.py",
                "scheduler/loaders.py", "scheduler/compare.py"]


def check_project_is_up_to_date():
    """Fail early with a clear message if the scheduler/ folder predates the estimator update."""
    import dataclasses
    ok = "estimator" in {f.name for f in dataclasses.fields(Settings)}
    try:
        from scheduler.estimator import RequestedTimeEstimator  # noqa: F401
    except ImportError:
        ok = False
    if not ok:
        raise SystemExit("Your scheduler/ folder is out of date (it has no 'estimator' setting).\n"
                         "Copy these files from the latest update into your project, replacing the old ones:\n  "
                         + "\n  ".join(NEEDED_FILES))


def quality(engine):
    est = pd.Series([j.est for j in engine.done], dtype=float)
    act = pd.Series([j.burst for j in engine.done], dtype=float)
    return dict(median_abs_rel_error=float(((est - act).abs() / act).median()),
                spearman_rank_corr=float(est.corr(act, method="spearman")),
                median_over_under=float((est / act).median()))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("log")
    ap.add_argument("--slices", type=int, default=30)
    ap.add_argument("--jobs", type=int, default=200)
    ap.add_argument("--load", type=float, default=0.9)
    ap.add_argument("--check-factor", type=float, default=0.5)
    ap.add_argument("--out", default="results_estimators")
    a = ap.parse_args()
    check_project_is_up_to_date()
    if not os.path.isfile(a.log):
        raise SystemExit(f"File not found: {a.log!r}\nRun this from the folder that contains the log, or give "
                         f"the full path, e.g. C:\\Users\\you\\Downloads\\SDSC-SP2-1998-4_swf.gz")
    os.makedirs(a.out, exist_ok=True)
    ck_runs, ck_q = f"{a.out}/ck_runs.csv", f"{a.out}/ck_quality.csv"
    rows = pd.read_csv(ck_runs).to_dict("records") if os.path.exists(ck_runs) else []
    qrows = pd.read_csv(ck_q).to_dict("records") if os.path.exists(ck_q) else []
    done = {r["slice"] for r in rows}

    for k in range(a.slices):
        if k in done:
            continue
        try:
            jobs = load_swf(a.log, max_jobs=a.jobs, start=k * a.jobs)
        except WorkloadError:             # ran past the end of the log
            break
        if len(jobs) < a.jobs // 2:
            break
        jobs = rescale_load(jobs, a.load)
        iv = max(10, round(float(np.mean([j.burst for j in jobs])) * a.check_factor))
        for mode in MODES:
            full = mode == "history"
            E = compare(jobs, Settings(check_interval=iv, estimator=mode), include_cheating_reference=full,
                        only=None if full else ["SJF", "Shadow (adaptive)"])
            for name, e in E.items():
                label = name
                if name == "SJF":
                    label = f"SJF [{mode}]"
                elif name == "Shadow (adaptive)":
                    label = f"Shadow [{mode}]"
                elif name == "Rule router (old design)":
                    label = "Rule router [history]"
                m = e.metrics()
                rows.append(dict(slice=k, method=label, avg_wait=m["avg_wait"], p95_wait=m["p95_wait"],
                                 max_wait=m["max_wait"], rule_changes=m["policy_switches"]))
            qrows.append(dict(slice=k, estimator=mode, **quality(E["SJF"])))
        pd.DataFrame(rows).to_csv(ck_runs, index=False)
        pd.DataFrame(qrows).to_csv(ck_q, index=False)
        print(f"  slice {k} done", flush=True)

    if not rows:
        raise SystemExit("No usable slices were produced. Check --jobs/--slices and that the file is a valid SWF log.")
    df, q = pd.DataFrame(rows), pd.DataFrame(qrows)
    order = ["FCFS", "RR4", "SJF [history]", "SJF [requested]", "SJF [corrected]", "Rule router [history]",
             "Shadow [history]", "Shadow [requested]", "Shadow [corrected]", "SJF* (cheats: true bursts)"]
    order = [o for o in order if o in set(df.method)]
    g = df.groupby("method").agg(slices=("slice", "nunique"), avg_wait=("avg_wait", "mean"),
                                 median_avg_wait=("avg_wait", "median"), p95_wait=("p95_wait", "mean"),
                                 max_wait=("max_wait", "mean"), rule_changes=("rule_changes", "mean")).loc[order]
    out = [f"# Estimator study: {os.path.basename(a.log)}\n",
           f"{df.slice.nunique()} slices x {a.jobs} jobs, arrivals rescaled to load {a.load}. "
           f"Controller check interval = {a.check_factor} x mean burst. Nothing tuned on this log.\n",
           "## Scheduling results (average waiting time in ticks, lower is better)\n", g.round(1).to_markdown(),
           "\n## How good are the guesses?\n",
           "median_abs_rel_error: typical |guess - truth| / truth (0 = perfect). spearman_rank_corr: how well the "
           "guesses ORDER the jobs (1 = perfect; SJF only needs the order). median_over_under: median guess/truth "
           "(1 = unbiased, >1 = overestimates).\n",
           q.groupby("estimator")[["median_abs_rel_error", "spearman_rank_corr", "median_over_under"]]
           .mean().loc[MODES].round(2).to_markdown()]
    pv = df.pivot(index="slice", columns="method", values="avg_wait")
    pairs = [("SJF [requested]", "SJF [history]"), ("SJF [corrected]", "SJF [history]"),
             ("Shadow [requested]", "Shadow [history]"), ("Shadow [corrected]", "Shadow [history]"),
             ("Shadow [requested]", "SJF [requested]"), ("Shadow [corrected]", "SJF [corrected]"),
             ("Shadow [requested]", "RR4"), ("Shadow [corrected]", "RR4"),
             ("SJF [corrected]", "RR4"), ("SJF [requested]", "RR4")]
    prow = []
    for x, y in pairs:
        mean, lo, hi, win = paired_ci(pv[x], pv[y])
        prow.append(dict(A=x, B=y, mean_diff_A_minus_B=round(mean, 1), ci95=f"[{lo:.1f}, {hi:.1f}]",
                         A_wins=f"{win:.0%}", verdict="A better" if hi < 0 else ("A worse" if lo > 0 else "no clear difference")))
    out += ["\n## Paired comparisons on avg wait (negative diff = A better; 95% bootstrap CI over slices)\n",
            pd.DataFrame(prow).to_markdown(index=False)]
    open(f"{a.out}/estimator_summary.md", "w").write("\n".join(out))
    df.to_csv(f"{a.out}/estimator_runs.csv", index=False)
    print("\n".join(out))


if __name__ == "__main__":
    main()
