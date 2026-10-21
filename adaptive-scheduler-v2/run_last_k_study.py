"""Why does averaging the user's last TWO jobs work? Test different window sizes.

    python -m experiments.run_last_k_study LOG.swf[.gz] --slices 30 --jobs 200 --load 0.9

SJF (non-adaptive) is run with the Tsafrir predictor using the last k = 1, 2, 3, 5, 10, 20 jobs, plus
the other estimators for reference. Only the quality of the guesses changes between runs, so any
difference in waiting time is caused by the guesses.
"""
import argparse
import os

import numpy as np
import pandas as pd

from experiments.run_estimator_study import paired_ci, quality
from scheduler.compare import make_estimator
from scheduler.controllers import FixedController
from scheduler.engine import Engine
from scheduler.loaders import load_swf, rescale_load, WorkloadError
from scheduler.policies import SJF

WINDOWS = [1, 2, 3, 5, 10, 20]
EXTRA = ["history", "last2", "tsafrir-nocap", "requested", "corrected"]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("log")
    ap.add_argument("--slices", type=int, default=30)
    ap.add_argument("--jobs", type=int, default=200)
    ap.add_argument("--load", type=float, default=0.9)
    ap.add_argument("--out", default="results_last_k")
    a = ap.parse_args()
    if not os.path.isfile(a.log):
        raise SystemExit(f"File not found: {a.log!r}")
    os.makedirs(a.out, exist_ok=True)
    specs = [f"tsafrir-k{k}" for k in WINDOWS] + EXTRA
    rows, qrows = [], []
    for k in range(a.slices):
        try:
            jobs = load_swf(a.log, max_jobs=a.jobs, start=k * a.jobs)
        except WorkloadError:
            break
        if len(jobs) < a.jobs // 2:
            break
        jobs = rescale_load(jobs, a.load)
        for spec in specs:
            e = Engine(jobs, FixedController(SJF()), estimator=make_estimator(spec), cs_cost=1,
                       check_interval=10 ** 9).run()
            m = e.metrics()
            rows.append(dict(slice=k, estimator=spec, avg_wait=m["avg_wait"], p95_wait=m["p95_wait"]))
            qrows.append(dict(slice=k, estimator=spec, **quality(e)))
        e = Engine(jobs, FixedController(SJF(use_true=True)), cs_cost=1, check_interval=10 ** 9).run()
        rows.append(dict(slice=k, estimator="SJF* (true bursts)", avg_wait=e.metrics()["avg_wait"],
                         p95_wait=e.metrics()["p95_wait"]))
    if not rows:
        raise SystemExit("No usable slices were produced.")
    df, q = pd.DataFrame(rows), pd.DataFrame(qrows)
    order = [f"tsafrir-k{k}" for k in WINDOWS] + EXTRA + ["SJF* (true bursts)"]
    g = df.groupby("estimator").agg(slices=("slice", "nunique"), avg_wait=("avg_wait", "mean"),
                                    median_avg_wait=("avg_wait", "median"), p95_wait=("p95_wait", "mean")).loc[order]
    qq = q.groupby("estimator")[["median_abs_rel_error", "spearman_rank_corr", "median_over_under"]].mean()
    out = [f"# Window-size study: {os.path.basename(a.log)}\n",
           f"{df.slice.nunique()} slices x {a.jobs} jobs, load {a.load}, SJF with different burst guesses.\n",
           "## Average wait (ticks)\n", g.round(1).to_markdown(),
           "\n## Guess quality\n", qq.loc[[o for o in order if o in qq.index]].round(2).to_markdown()]
    pv = df.pivot(index="slice", columns="estimator", values="avg_wait")
    prow = []
    for x, y in [("tsafrir-k2", "tsafrir-k1"), ("tsafrir-k2", "tsafrir-k3"), ("tsafrir-k2", "tsafrir-k5"),
                 ("tsafrir-k2", "tsafrir-k10"), ("tsafrir-k2", "tsafrir-k20"), ("tsafrir-k2", "history"),
                 ("tsafrir-k2", "last2"), ("tsafrir-k2", "tsafrir-nocap"), ("corrected", "tsafrir-k2")]:
        mean, lo, hi, win = paired_ci(pv[x], pv[y])
        prow.append(dict(A=x, B=y, mean_diff_A_minus_B=round(mean, 1), ci95=f"[{lo:.1f}, {hi:.1f}]", A_wins=f"{win:.0%}",
                         verdict="A better" if hi < 0 else ("A worse" if lo > 0 else "no clear difference")))
    out += ["\n## Paired comparisons on avg wait (negative = A better)\n", pd.DataFrame(prow).to_markdown(index=False)]
    open(f"{a.out}/{os.path.basename(a.log).split('.')[0]}_summary.md", "w").write("\n".join(out))
    df.to_csv(f"{a.out}/{os.path.basename(a.log).split('.')[0]}_runs.csv", index=False)
    print("\n".join(out))


if __name__ == "__main__":
    main()
