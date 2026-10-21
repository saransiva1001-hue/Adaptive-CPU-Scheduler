"""Controllers decide WHICH policy is active. (Earlier I called this the 'router'.)

FixedController   - always one rule (the normal OS way, our baseline)
RuleController    - the old design: hand-written if/else on a workload signature
ShadowController  - the new design: replay recent history under each candidate rule
                    (a "trial run"), switch only if one clearly does better, and
                    optionally honour a requirement and distrust bad burst guesses.
"""
from dataclasses import dataclass
from statistics import mean, pstdev

from .engine import Engine
from .metrics import metrics_from_jobs


class Controller:
    def initial_policy(self):
        raise NotImplementedError

    def select(self, eng):
        return eng.policy


class FixedController(Controller):
    def __init__(self, policy):
        self.policy = policy

    def initial_policy(self):
        return self.policy


class RuleController(Controller):
    """The earlier design, adapted to honest estimates: if/else on the ready queue."""

    def __init__(self, fcfs, sjf):
        self.fcfs, self.sjf = fcfs, sjf

    def initial_policy(self):
        return self.sjf

    def select(self, eng):
        ests = [j.est for j in eng.ready]
        if len(ests) < 3:
            return eng.policy
        avg = mean(ests)
        cv = pstdev(ests) / avg if avg else 0
        if cv >= 0.8:
            return self.sjf
        if avg > 12:
            return self.fcfs
        return self.sjf


@dataclass
class Requirement:
    """e.g. Requirement('p95_wait', 12): 'the 95th-percentile wait must stay <= 12'."""
    metric: str
    limit: float


def replay(jobs, policy, cs_cost=1):
    """Re-simulate a small set of jobs under one policy. No estimator: jobs already
    carry the estimates the scheduler really had."""
    e = Engine(jobs, FixedController(policy), estimator=None, cs_cost=cs_cost,
               check_interval=10 ** 9).run()
    return metrics_from_jobs(e.done)


class ShadowController(Controller):
    def __init__(self, candidates, window_jobs=12, min_jobs=4, margin=0.05, patience=2,
                 objective="avg_wait", requirement=None, guard=False,
                 guard_threshold=0.9, cs_cost=1, initial=None):
        self.candidates = candidates
        self.window_jobs = window_jobs
        self.min_jobs = min_jobs
        self.margin = margin
        self.patience = patience
        self.objective = objective
        self.requirement = requirement
        self.guard = guard
        self.guard_threshold = guard_threshold
        self.cs_cost = cs_cost
        self.initial = initial or candidates[0]
        self.last_scores = {}
        self._challenger = None
        self._streak = 0

    def initial_policy(self):
        return self.initial

    def _score(self, m):
        """(violation, objective): lower is better, compared in that order."""
        viol = 0.0
        if self.requirement:
            viol = max(0.0, m[self.requirement.metric] - self.requirement.limit) / self.requirement.limit
        return (viol, m[self.objective])

    def _improves(self, new, cur):
        if new[0] < cur[0] - 1e-9:
            return True
        if new[0] > cur[0] + 1e-9:
            return False
        return new[1] < cur[1] * (1 - self.margin)

    def select(self, eng):
        jobs = eng.recent_jobs(self.window_jobs)
        if len(jobs) < self.min_jobs:
            return eng.policy

        allowed = list(self.candidates)
        if self.guard and eng.estimator and eng.estimator.recent_error > self.guard_threshold:
            safe = [p for p in allowed if not p.uses_estimates]
            allowed = safe or allowed                       # distrust bad guesses

        cur = eng.policy
        pool = {p.name: p for p in allowed}
        pool.setdefault(cur.name, cur)
        self.last_scores = {n: self._score(replay(jobs, p, self.cs_cost)) for n, p in pool.items()}

        if cur.name not in {p.name for p in allowed}:       # current rule is now untrusted
            best = min(allowed, key=lambda p: self.last_scores[p.name])
            self._challenger, self._streak = None, 0
            return best

        best = min(allowed, key=lambda p: (self.last_scores[p.name], p.name != cur.name))
        if best.name != cur.name and self._improves(self.last_scores[best.name], self.last_scores[cur.name]):
            if self._challenger == best.name:
                self._streak += 1
            else:
                self._challenger, self._streak = best.name, 1
            if self._streak >= self.patience:
                self._challenger, self._streak = None, 0
                return best
        else:
            self._challenger, self._streak = None, 0
        return cur
