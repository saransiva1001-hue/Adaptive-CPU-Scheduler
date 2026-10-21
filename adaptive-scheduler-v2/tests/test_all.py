"""Plain-assert tests.  Run:  python -m tests.test_all"""
import random

from scheduler.controllers import (Controller, FixedController, Requirement,
                                   ShadowController, replay)
from scheduler.engine import Engine
from scheduler.estimator import BurstEstimator
from scheduler.job import Job
from scheduler.policies import FCFS, RoundRobin, SJF
from scheduler.workloads import generate


def avg_wait(jobs, pol, cs=0):
    e = Engine(jobs, FixedController(pol), estimator=None, cs_cost=cs, check_interval=10 ** 9).run()
    return e.metrics()["avg_wait"]


def approx(a, b, tol=1e-6):
    return abs(a - b) < tol


BOOK = lambda: [Job(1, 0, 24), Job(2, 0, 3), Job(3, 0, 3)]          # Silberschatz example
EX_A = lambda: [Job(1, 0, 12), Job(2, 1, 2), Job(3, 2, 3), Job(4, 3, 2), Job(5, 4, 3)]
EX_A2 = lambda: [Job(1, 0, 10), Job(2, 0, 11), Job(3, 0, 9), Job(4, 0, 10), Job(5, 0, 12)]


def test_textbook_values():
    assert approx(avg_wait(BOOK(), FCFS()), 17)
    assert approx(avg_wait(BOOK(), SJF(True)), 3)
    assert approx(avg_wait(BOOK(), RoundRobin(4)), 17 / 3)


def test_worked_examples_from_the_plan():
    assert approx(avg_wait(EX_A(), FCFS()), 10.4)
    assert approx(avg_wait(EX_A(), SJF(True)), 10.2)
    assert approx(avg_wait(EX_A(), RoundRobin(3)), 5.8)
    assert approx(avg_wait(EX_A2(), FCFS()), 20.2)
    assert approx(avg_wait(EX_A2(), SJF(True)), 19.4)
    assert approx(avg_wait(EX_A2(), RoundRobin(3)), 36.4)


def test_context_switch_cost_is_charged():
    assert avg_wait(BOOK(), RoundRobin(4), cs=1) > avg_wait(BOOK(), RoundRobin(4), cs=0)
    assert approx(avg_wait(BOOK(), RoundRobin(4), cs=1), 23 / 3)


def test_idle_gap_is_handled():
    jobs = [Job(1, 0, 2), Job(2, 50, 3)]
    e = Engine(jobs, FixedController(FCFS()), estimator=None, cs_cost=0, check_interval=10 ** 9).run()
    assert e.metrics()["avg_wait"] == 0
    assert max(j.finish for j in e.done) == 53


def test_estimator_matches_textbook_formula():
    est = BurstEstimator(alpha=0.5, default=10)
    preds = []
    for actual in [6, 4, 6, 4]:
        preds.append(est.predict("a"))
        est.update("a", est.predict("a"), actual)
    assert preds == [10, 8, 6, 6] and est.predict("a") == 5


def test_one_surprise_poisons_the_next_guess():
    est = BurstEstimator(alpha=0.5, default=3)
    for actual in [3, 3, 3, 3]:
        est.update("a", est.predict("a"), actual)
    guess = est.predict("a")
    est.update("a", guess, 40)
    assert guess == 3 and est.predict("a") == 21.5
    assert est.recent_error > 0.15


class Stub:
    """Minimal stand-in for the engine, so the controller can be tested on fixed history."""
    def __init__(self, jobs, policy, estimator=None):
        self.jobs, self.policy, self.estimator = jobs, policy, estimator

    def recent_jobs(self, k):
        return [j.fresh() for j in self.jobs]


def with_est(jobs):
    for j in jobs:
        j.est = float(j.burst)
    return jobs


def test_shadow_switches_when_trial_run_shows_big_gain():
    cands = [FCFS(), SJF(), RoundRobin(3)]
    c = ShadowController(cands, patience=1, cs_cost=0, min_jobs=1)
    assert c.select(Stub(with_est(EX_A()), cands[0])).name == "RR3"       # 10.4 -> 5.8


def test_shadow_stays_when_gain_is_tiny_or_negative():
    cands = [FCFS(), SJF(), RoundRobin(3)]
    c = ShadowController(cands, patience=1, cs_cost=0, min_jobs=1)
    assert c.select(Stub(with_est(EX_A2()), cands[0])).name == "FCFS"     # SJF only 4% better


def test_hysteresis_needs_repeated_evidence():
    cands = [FCFS(), SJF(), RoundRobin(3)]
    c = ShadowController(cands, patience=2, cs_cost=0, min_jobs=1)
    stub = Stub(with_est(EX_A()), cands[0])
    assert c.select(stub).name == "FCFS"        # first sighting: not enough
    assert c.select(stub).name == "RR3"         # second sighting: switch


def test_requirement_filters_rules_that_break_it():
    cands = [FCFS(), SJF(), RoundRobin(3)]
    c = ShadowController(cands, requirement=Requirement("max_wait", 12), cs_cost=0, min_jobs=1)
    jobs = with_est(EX_A())
    viol = {p.name: c._score(replay(jobs, p, 0))[0] for p in cands}
    assert viol["FCFS"] > 0 and viol["SJF"] > 0 and viol["RR3"] == 0      # max waits 15, 15, 10


def test_guard_drops_estimate_based_rules_when_guesses_are_bad():
    est = BurstEstimator()
    for _ in range(8):
        est.errors.append(2.0)                                            # terrible guesses
    cands = [FCFS(), SJF(), RoundRobin(3)]
    c = ShadowController(cands, guard=True, patience=1, cs_cost=0, min_jobs=1)
    chosen = c.select(Stub(with_est(EX_A2()), cands[1], estimator=est))   # currently on SJF
    assert chosen.name != "SJF"


class Flipper(Controller):
    """Silly controller that changes rule at every check: stress test for mid-run switching."""
    def __init__(self):
        self.pols, self.k = [FCFS(), SJF(), RoundRobin(3), RoundRobin(7)], 0

    def initial_policy(self):
        return self.pols[0]

    def select(self, eng):
        self.k += 1
        return self.pols[self.k % len(self.pols)]


def check_invariants(jobs, e):
    n = len(jobs)
    assert len(e.done) == n
    assert e.busy == sum(j.burst for j in jobs)
    for j in e.done:
        assert j.start >= j.arrival and j.finish >= j.arrival + j.burst
        assert j.wait >= 0 and j.remaining == 0
    assert e.metrics()["utilisation"] <= 1.0 + 1e-9


def test_invariants_under_random_workloads_and_midrun_switching():
    for seed in range(150):
        r = random.Random(seed)
        jobs = [Job(i + 1, r.randint(0, 40), r.randint(1, 25), r.choice("ab")) for i in range(r.randint(1, 15))]
        for ctrl in (FixedController(FCFS()), FixedController(SJF()), FixedController(RoundRobin(r.randint(1, 8))),
                     Flipper(), ShadowController([FCFS(), SJF(), RoundRobin(4)], patience=1)):
            e = Engine(jobs, ctrl, cs_cost=r.choice([0, 1, 2]), switch_penalty=r.choice([0, 1]),
                       check_interval=r.choice([1, 5, 10])).run()
            check_invariants(jobs, e)


def test_runs_are_reproducible():
    a = Engine(generate("phased", 7), ShadowController([FCFS(), SJF(), RoundRobin(4)])).run().metrics()
    b = Engine(generate("phased", 7), ShadowController([FCFS(), SJF(), RoundRobin(4)])).run().metrics()
    a.pop("controller_ms"); b.pop("controller_ms")
    assert a == b


if __name__ == "__main__":
    tests = [(k, v) for k, v in sorted(globals().items()) if k.startswith("test_")]
    for name, fn in tests:
        fn()
        print("PASS ", name)
    print(f"\nAll {len(tests)} tests passed.")
