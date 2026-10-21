"""Run every method on one workload. Used by the UI (and handy for your own scripts)."""
from dataclasses import dataclass

from .controllers import FixedController, RuleController, ShadowController
from .engine import Engine
import re

from .estimator import BurstEstimator, Last2Estimator, RequestedTimeEstimator, TsafrirEstimator
from .policies import FCFS, RoundRobin, SJF


@dataclass
class Settings:
    quantum: int = 4              # Round Robin time slice
    cs_cost: int = 1              # ticks lost on every context switch
    switch_penalty: int = 1       # ticks lost when the scheduler changes rule
    check_interval: int = 10      # how often the controller looks at the system
    window_jobs: int = 12         # how many recent arrivals the trial run replays
    margin: float = 0.05          # another rule must look this much better to be considered
    patience: int = 2             # ... on this many checks in a row
    initial: str = "SJF"          # rule the shadow scheduler starts with
    estimator: str = "history"    # burst guesses: history | last2 | tsafrir | requested | corrected


def _pool(q):
    return [FCFS(), SJF(), RoundRobin(q)]


def make_estimator(mode):
    """history | last2 | tsafrir | tsafrir-nocap | tsafrir-k<N> (window N) | requested | corrected"""
    if mode == "history":
        return BurstEstimator()
    if mode == "last2":
        return Last2Estimator()
    if mode == "tsafrir":
        return TsafrirEstimator()
    if mode == "tsafrir-nocap":
        return TsafrirEstimator(cap_at_request=False)
    m = re.fullmatch(r"tsafrir-k(\d+)", mode)
    if m:
        return TsafrirEstimator(window=int(m.group(1)))
    if mode in ("requested", "corrected"):
        return RequestedTimeEstimator(mode)       # jobs without a requested time fall back to history
    raise ValueError(f"unknown estimator {mode!r}")


def compare(jobs, s: Settings = Settings(), include_cheating_reference=True, only=None):
    """Returns {method name: Engine} (engine.metrics() has the numbers).
    only: optional list of method names to run (saves time)."""
    f, sj, rr = _pool(s.quantum)
    pool = _pool(s.quantum)
    start = {p.name: p for p in pool}.get(s.initial, pool[1])
    methods = {
        "FCFS": FixedController(f),
        "SJF": FixedController(sj),
        rr.name: FixedController(rr),
        "Rule router (old design)": RuleController(FCFS(), SJF()),
        "Shadow (adaptive)": ShadowController(pool, window_jobs=s.window_jobs, margin=s.margin,
                                              patience=s.patience, cs_cost=s.cs_cost, initial=start),
    }
    if include_cheating_reference:
        methods["SJF* (cheats: true bursts)"] = FixedController(SJF(use_true=True))
    return {name: Engine(jobs, ctrl, estimator=make_estimator(s.estimator), cs_cost=s.cs_cost,
                         switch_penalty=s.switch_penalty, check_interval=s.check_interval).run()
            for name, ctrl in methods.items() if only is None or name in only}


def policy_segments(engine):
    """[(start, end, policy name)] describing which rule was active when."""
    end = max(j.finish for j in engine.done)
    cur = engine.switch_log[0][1] if engine.switch_log else engine.policy.name
    segs, t = [], 0
    for ts, _old, new in engine.switch_log:
        segs.append((t, ts, cur))
        t, cur = ts, new
    segs.append((t, end, cur))
    return segs
