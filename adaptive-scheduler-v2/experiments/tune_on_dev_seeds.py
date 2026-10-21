"""Pick controller settings using DEV seeds (1000+), never the seeds used for the report (0..N).
Tuning on the reported seeds would quietly inflate the results.

    python -m experiments.tune_on_dev_seeds
Score = mean regret (%) over all workloads vs the best fixed rule in hindsight
        + 0.5 * worst-workload regret (we want robustness, not just a good average).
"""
import numpy as np

from experiments.run_experiments import CHECK, CS, SWITCH_PENALTY, pool
from scheduler.controllers import FixedController, ShadowController
from scheduler.engine import Engine
from scheduler.workloads import WORKLOADS, generate

DEV = list(range(1000, 1020))


def run(jobs, ctrl):
    return Engine(jobs, ctrl, cs_cost=CS, switch_penalty=SWITCH_PENALTY,
                  check_interval=CHECK).run().metrics()["avg_wait"]


def evaluate(make):
    per_w = []
    for w in WORKLOADS:
        reg = []
        for s in DEV:
            jobs = generate(w, s)
            best = min(run(jobs, FixedController(p)) for p in pool())
            reg.append((run(jobs, make()) - best) / best * 100)
        per_w.append(np.mean(reg))
    return np.mean(per_w), max(per_w), np.mean(per_w) + 0.5 * max(per_w)


def mk(**kw):
    init_name = kw.pop("initial", "FCFS")
    def f():
        p = pool()
        init = {x.name: x for x in p}[init_name]
        return ShadowController(p, initial=init, **kw)
    return f


if __name__ == "__main__":
    base = dict(initial="SJF", window_jobs=12, margin=0.05, patience=2, guard=False)
    sweeps = [("initial", ["FCFS", "SJF", "RR4"]), ("window_jobs", [8, 12, 20]),
              ("margin", [0.0, 0.05, 0.15]), ("patience", [1, 2, 3])]
    print(f"{'setting':32s} mean%   worst%  score")
    for key, vals in sweeps:
        for v in vals:
            cfg = dict(base, **{key: v})
            m, w, s = evaluate(mk(**dict(cfg)))
            print(f"{key + '=' + str(v):32s} {m:6.1f} {w:7.1f} {s:6.1f}")
    print("-- guard threshold (with base settings)")
    for th in [0.6, 0.9, 1.2, 1.5]:
        cfg = dict(base, guard=True, guard_threshold=th)
        m, w, s = evaluate(mk(**cfg))
        print(f"{'guard th=' + str(th):32s} {m:6.1f} {w:7.1f} {s:6.1f}")
