"""Cold start vs warm start: does the estimator ranking change once history exists?

    python -m experiments.run_warm_study LOG.swf[.gz] --slices 30 --jobs 200 --warm 0 1000

In the earlier studies every 200-job slice began with EMPTY history, so most guesses were
first-job guesses. A real scheduler has long history. Here each estimator can first be fed the
`warm` jobs that preceded the slice (observed only, never scheduled), then the slice is scheduled
with SJF. All variants use the same time scale and the same jobs.
"""
import argparse
import os

import numpy as np
import pandas as pd

from experiments.run_estimator_ablation import EwmaWithRequestFallback
from experiments.run_estimator_study import paired_ci, quality
from scheduler.controllers import FixedController
from scheduler.engine import Engine
from scheduler.estimator import BurstEstimator, RequestedTimeEstimator, TsafrirEstimator
from scheduler.job import Job
from scheduler.loaders import load_swf, offered_load
from scheduler.policies import SJF

VARIANTS = {
    "old running average": lambda: BurstEstimator(),
    "running average + request for new users": lambda: EwmaWithRequestFallback(),
    "tsafrir k=1": lambda: TsafrirEstimator(window=1),
    "tsafrir k=2 (paper)": lambda: TsafrirEstimator(window=2),
    "tsafrir k=3": lambda: TsafrirEstimator(window=3),
    "tsafrir k=5": lambda: TsafrirEstimator(window=5),
    "tsafrir k=10": lambda: TsafrirEstimator(window=10),
    "tsafrir k=2, requests ignored": lambda: TsafrirEstimator(window=2, use_request=False),
    "requested": lambda: RequestedTimeEstimator("requested"),
    "corrected": lambda: RequestedTimeEstimator("corrected"),
}


def make_slice(log, k, n, warm, tps, load):
    start = k * n
    w = min(warm, start)
    rows = load_swf(log, max_jobs=w + n, start=start - w, ticks_per_second=tps)
    hist, sl = rows[:w], rows[w:]
    t0 = sl[0].arrival
    span = max(j.arrival for j in sl) - t0 + 1
    factor = (sum(j.burst for j in sl) / span) / load          # same rescaling as rescale_load
    mk = lambda j: Job(j.pid, int(round((j.arrival - t0) * factor)), j.burst, j.cls, req=j.req)
    return [mk(j) for j in hist], [mk(j) for j in sl]


def run_variant(factory, hist, sl):
    est = factory()
    for j in hist:                                  # observe-only warm-up, in submission order
        j.est = est.estimate(j)
        est.observe(j)
    e = Engine(sl, FixedController(SJF()), estimator=est, cs_cost=1, check_interval=10 ** 9).run()
    return e


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("log")
    ap.add_argument("--slices", type=int, default=30)
    ap.add_argument("--jobs", type=int, default=200)
    ap.add_argument("--load", type=float, default=0.9)
    ap.add_argument("--warm", type=int, nargs="+", default=[0, 1000])
    ap.add_argument("--out", default="results_last_k")
    a = ap.parse_args()
    if not os.path.isfile(a.log):
        raise SystemExit(f"File not found: {a.log!r}")
    os.makedirs(a.out, exist_ok=True)
    secs = [j.burst for j in load_swf(a.log, max_jobs=10 ** 9, ticks_per_second=1.0)]
    tps = 8.0 / float(np.median(secs))                  # one time scale for the whole log
    name = os.path.basename(a.log).split(".")[0]
    out = [f"# Cold vs warm start: {name}\n", f"{a.slices} slices x {a.jobs} jobs, load {a.load}, SJF, one time scale "
           f"for the whole log (median job = 8 ticks). warm = number of earlier jobs each estimator may learn from first.\n"]
    for warm in a.warm:
        rows, qrows = [], []
        for k in range(a.slices):
            try:
                hist, sl = make_slice(a.log, k, a.jobs, warm, tps, a.load)
            except Exception:
                break
            if len(sl) < a.jobs // 2:
                break
            for vname, mk in VARIANTS.items():
                e = run_variant(mk, [j.fresh() for j in hist], [j.fresh() for j in sl])
                rows.append(dict(slice=k, variant=vname, avg_wait=e.metrics()["avg_wait"]))
                qrows.append(dict(slice=k, variant=vname, **quality(e)))
            e = Engine([j.fresh() for j in sl], FixedController(SJF(use_true=True)), cs_cost=1, check_interval=10 ** 9).run()
            rows.append(dict(slice=k, variant="SJF* (true bursts)", avg_wait=e.metrics()["avg_wait"]))
        df, q = pd.DataFrame(rows), pd.DataFrame(qrows)
        order = list(VARIANTS) + ["SJF* (true bursts)"]
        g = df.groupby("variant").agg(avg_wait=("avg_wait", "mean"), median=("avg_wait", "median")).loc[order]
        qq = q.groupby("variant")[["median_abs_rel_error", "spearman_rank_corr"]].mean().loc[list(VARIANTS)]
        pv = df.pivot(index="slice", columns="variant", values="avg_wait")
        pairs = [("tsafrir k=2 (paper)", "old running average"), ("tsafrir k=2 (paper)", "running average + request for new users"),
                 ("tsafrir k=2 (paper)", "tsafrir k=1"), ("tsafrir k=2 (paper)", "tsafrir k=5"), ("tsafrir k=2 (paper)", "tsafrir k=10"),
                 ("tsafrir k=2, requests ignored", "old running average"), ("corrected", "tsafrir k=2 (paper)")]
        prow = []
        for x, y in pairs:
            mean, lo, hi, win = paired_ci(pv[x], pv[y])
            prow.append(dict(A=x, B=y, diff=round(mean, 1), ci95=f"[{lo:.1f}, {hi:.1f}]", A_wins=f"{win:.0%}",
                             verdict="A better" if hi < 0 else ("A worse" if lo > 0 else "no clear difference")))
        out += [f"\n## warm = {warm} earlier jobs\n", "Average wait (ticks):\n", g.round(1).to_markdown(),
                "\nGuess quality:\n", qq.round(2).to_markdown(), "\nPaired comparisons (negative diff = A better):\n",
                pd.DataFrame(prow).to_markdown(index=False)]
    open(f"{a.out}/{name}_warm.md", "w").write("\n".join(out))
    print("\n".join(out))


if __name__ == "__main__":
    main()
