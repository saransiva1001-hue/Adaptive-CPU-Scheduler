"""Where does the gain over the old running-average estimator come from?

    python -m experiments.run_estimator_ablation LOG.swf[.gz] --slices 30 --jobs 200 --load 0.9

Separates two things the Tsafrir predictor does at once:
  (a) averaging the user's last k finished jobs (history),
  (b) using the user's REQUEST when there is no history yet (and capping at it).
SJF is run with each variant; only the guesses differ.
"""
import argparse
import os

import pandas as pd

from experiments.run_estimator_study import paired_ci, quality
from scheduler.controllers import FixedController
from scheduler.engine import Engine
from scheduler.estimator import BurstEstimator, TsafrirEstimator
from scheduler.loaders import WorkloadError, load_swf, rescale_load
from scheduler.policies import SJF


class EwmaWithRequestFallback(BurstEstimator):
    """The OLD running-average estimator, but a user's first job is guessed from its request."""

    def estimate(self, job):
        if job.cls not in self.tau and job.req:
            return float(job.req)
        return self.predict(job.cls)


VARIANTS = {
    "A. running average, default 8 for new users (old)": lambda: BurstEstimator(),
    "B. running average, request for new users": lambda: EwmaWithRequestFallback(),
    "C. last-2 average, default 8 for new users (no requests at all)": lambda: TsafrirEstimator(use_request=False),
    "D. last-2 average + request fallback, no cap": lambda: TsafrirEstimator(cap_at_request=False),
    "E. full Tsafrir (last-2 + request fallback + cap)": lambda: TsafrirEstimator(),
}


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
    rows, qrows = [], []
    for k in range(a.slices):
        try:
            jobs = load_swf(a.log, max_jobs=a.jobs, start=k * a.jobs)
        except WorkloadError:
            break
        if len(jobs) < a.jobs // 2:
            break
        jobs = rescale_load(jobs, a.load)
        for name, mk in VARIANTS.items():
            e = Engine(jobs, FixedController(SJF()), estimator=mk(), cs_cost=1, check_interval=10 ** 9).run()
            rows.append(dict(slice=k, variant=name, avg_wait=e.metrics()["avg_wait"]))
            qrows.append(dict(slice=k, variant=name, **quality(e)))
        e = Engine(jobs, FixedController(SJF(use_true=True)), cs_cost=1, check_interval=10 ** 9).run()
        rows.append(dict(slice=k, variant="SJF* (true bursts)", avg_wait=e.metrics()["avg_wait"]))
    if not rows:
        raise SystemExit("No usable slices were produced.")
    df, q = pd.DataFrame(rows), pd.DataFrame(qrows)
    order = list(VARIANTS) + ["SJF* (true bursts)"]
    g = df.groupby("variant").agg(avg_wait=("avg_wait", "mean"), median_avg_wait=("avg_wait", "median")).loc[order]
    qq = q.groupby("variant")[["median_abs_rel_error", "spearman_rank_corr"]].mean().loc[list(VARIANTS)]
    pv = df.pivot(index="slice", columns="variant", values="avg_wait")
    ks = list(VARIANTS)
    pairs = [(ks[1], ks[0]), (ks[2], ks[0]), (ks[2], ks[1]), (ks[3], ks[2]), (ks[4], ks[3]), (ks[4], ks[1])]
    prow = []
    for x, y in pairs:
        mean, lo, hi, win = paired_ci(pv[x], pv[y])
        prow.append(dict(A=x[:2], B=y[:2], mean_diff_A_minus_B=round(mean, 1), ci95=f"[{lo:.1f}, {hi:.1f}]",
                         A_wins=f"{win:.0%}", verdict="A better" if hi < 0 else ("A worse" if lo > 0 else "no clear difference")))
    out = [f"# Estimator ablation: {os.path.basename(a.log)}\n", f"{df.slice.nunique()} slices x {a.jobs} jobs, load {a.load}, SJF.\n",
           "## Average wait (ticks)\n", g.round(1).to_markdown(), "\n## Guess quality\n", qq.round(2).to_markdown(),
           "\n## Paired comparisons (letters = variants A-E above; negative = A better)\n", pd.DataFrame(prow).to_markdown(index=False)]
    name = os.path.basename(a.log).split(".")[0]
    open(f"{a.out}/{name}_ablation.md", "w").write("\n".join(out))
    print("\n".join(out))


if __name__ == "__main__":
    main()
