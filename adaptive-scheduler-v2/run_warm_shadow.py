"""Does 'always-SJF beats the adaptive selector when guesses are good' survive a WARM start?

    python -m experiments.run_warm_shadow LOG.swf[.gz] --slices 30 --jobs 200 --warm 1000

Each estimator first learns from the `warm` jobs before the slice, then FCFS, RR4, SJF and the
Shadow selector are run on the slice with that estimator.
"""
import argparse
import os

import numpy as np
import pandas as pd

from experiments.run_estimator_study import paired_ci
from experiments.run_warm_study import make_slice
from scheduler.controllers import FixedController, ShadowController
from scheduler.engine import Engine
from scheduler.estimator import BurstEstimator, RequestedTimeEstimator, TsafrirEstimator
from scheduler.loaders import load_swf
from scheduler.policies import FCFS, RoundRobin, SJF

EST = {"old running average": lambda: BurstEstimator(), "tsafrir k=2": lambda: TsafrirEstimator(),
       "corrected": lambda: RequestedTimeEstimator("corrected")}


def run(sl, hist, mk_est, ctrl, interval):
    est = mk_est()
    for j in hist:
        j.est = est.estimate(j)
        est.observe(j)
    return Engine(sl, ctrl, estimator=est, cs_cost=1, switch_penalty=1, check_interval=interval).run().metrics()["avg_wait"]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("log")
    ap.add_argument("--slices", type=int, default=30)
    ap.add_argument("--jobs", type=int, default=200)
    ap.add_argument("--load", type=float, default=0.9)
    ap.add_argument("--warm", type=int, default=1000)
    ap.add_argument("--out", default="results_last_k")
    a = ap.parse_args()
    if not os.path.isfile(a.log):
        raise SystemExit(f"File not found: {a.log!r}")
    os.makedirs(a.out, exist_ok=True)
    tps = 8.0 / float(np.median([j.burst for j in load_swf(a.log, max_jobs=10 ** 9, ticks_per_second=1.0)]))
    rows = []
    for k in range(a.slices):
        try:
            hist, sl = make_slice(a.log, k, a.jobs, a.warm, tps, a.load)
        except Exception:
            break
        if len(sl) < a.jobs // 2:
            break
        iv = max(10, round(float(np.mean([j.burst for j in sl])) * 0.5))
        fresh = lambda: ([j.fresh() for j in hist], [j.fresh() for j in sl])
        for m, ctrl in [("FCFS", lambda: FixedController(FCFS())), ("RR4", lambda: FixedController(RoundRobin(4)))]:
            h, s = fresh(); rows.append(dict(slice=k, estimator="(none needed)", method=m,
                                             avg_wait=run(s, h, lambda: BurstEstimator(), ctrl(), iv)))
        for en, mk in EST.items():
            h, s = fresh(); rows.append(dict(slice=k, estimator=en, method="SJF", avg_wait=run(s, h, mk, FixedController(SJF()), iv)))
            h, s = fresh(); pool = [FCFS(), SJF(), RoundRobin(4)]
            rows.append(dict(slice=k, estimator=en, method="Shadow", avg_wait=run(s, h, mk, ShadowController(pool, initial=pool[1]), iv)))
        print(f"  slice {k} done", flush=True)
    df = pd.DataFrame(rows)
    g = df.groupby(["estimator", "method"]).avg_wait.mean().round(1).to_frame()
    pv = df.pivot_table(index="slice", columns=["estimator", "method"], values="avg_wait")
    rr = df[df.method == "RR4"].set_index("slice").avg_wait
    out = [f"# Warm-start Shadow vs SJF: {os.path.basename(a.log)} (warm = {a.warm})\n", "## Average wait (ticks)\n", g.to_markdown(), "\n## Paired (negative = A better)\n"]
    prow = []
    for en in EST:
        for x, y, sx, sy in [("Shadow", "SJF", pv[(en, "Shadow")], pv[(en, "SJF")]), ("Shadow", "RR4", pv[(en, "Shadow")], rr),
                             ("SJF", "RR4", pv[(en, "SJF")], rr)]:
            mean, lo, hi, win = paired_ci(sx, sy)
            prow.append(dict(estimator=en, A=x, B=y, diff=round(mean, 1), ci95=f"[{lo:.1f}, {hi:.1f}]", A_wins=f"{win:.0%}",
                             verdict="A better" if hi < 0 else ("A worse" if lo > 0 else "no clear difference")))
    out.append(pd.DataFrame(prow).to_markdown(index=False))
    open(f"{a.out}/{os.path.basename(a.log).split('.')[0]}_warm_shadow.md", "w").write("\n".join(out))
    print("\n".join(out))


if __name__ == "__main__":
    main()
