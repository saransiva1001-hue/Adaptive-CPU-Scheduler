"""Tests for requested-time estimation.  Run:  python -m tests.test_estimators"""
import io

from scheduler.compare import Settings, compare, make_estimator
from scheduler.controllers import FixedController
from scheduler.engine import Engine
from scheduler.estimator import BurstEstimator, Last2Estimator, RequestedTimeEstimator, TsafrirEstimator
from scheduler.job import Job
from scheduler.loaders import load_swf, rescale_load
from scheduler.policies import SJF

SWF = """; test
1 0 0 100 1 -1 -1 1 400 -1 1 7 1 1 1 1 -1 -1
2 10 0 50 1 -1 -1 1 -1 -1 1 8 1 1 1 1 -1 -1
"""


def approx(a, b, tol=1e-9):
    return abs(a - b) < tol


def test_swf_requested_time_is_parsed_and_scaled():
    jobs = load_swf(io.StringIO(SWF), ticks_per_second=0.1)
    assert jobs[0].req == 40.0 and jobs[0].burst == 10        # 400 s and 100 s at 0.1 tick/s
    assert jobs[1].req is None                                # -1 means unknown


def test_requested_mode_returns_request_and_falls_back_to_history():
    est = RequestedTimeEstimator("requested", default=8)
    assert est.estimate(Job(1, 0, 5, "a", req=30.0)) == 30.0
    assert est.estimate(Job(2, 0, 5, "a")) == 8                # no request -> history default


def test_corrected_mode_learns_the_users_overestimate():
    est = RequestedTimeEstimator("corrected", ratio_alpha=0.3)
    first = Job(1, 0, 50, "a", req=100.0)
    first.est = est.estimate(first)
    assert first.est == 100.0                                  # nothing learned yet
    est.observe(first)                                         # used 50% of the request
    assert approx(est.ratio["a"], 0.3 * 0.5 + 0.7 * 1.0)       # 0.85
    assert approx(est.estimate(Job(2, 0, 9, "a", req=100.0)), 85.0)
    assert est.estimate(Job(3, 0, 9, "b", req=100.0)) == 100.0 * est.global_ratio   # new user: all-users ratio


def test_ratio_is_capped_when_a_job_overruns_its_request():
    est = RequestedTimeEstimator("corrected", ratio_alpha=1.0, ratio_cap=2.0)
    j = Job(1, 0, 500, "a", req=10.0)
    j.est = 10.0
    est.observe(j)
    assert est.ratio["a"] == 2.0


def test_engine_uses_requested_time_as_the_arrival_estimate():
    jobs = [Job(1, 0, 20, "u", req=60.0), Job(2, 1, 5, "u", req=10.0)]
    e = Engine(jobs, FixedController(SJF()), estimator=RequestedTimeEstimator("requested"),
               cs_cost=0, check_interval=10 ** 9).run()
    assert sorted((j.pid, j.est) for j in e.done) == [(1, 60.0), (2, 10.0)]


def test_sjf_order_follows_the_requests_not_the_hidden_burst():
    # job 2 is really shorter, but its user asked for MORE time -> SJF-by-request runs job 3 first
    jobs = [Job(1, 0, 10, "a", req=10.0), Job(2, 1, 2, "b", req=90.0), Job(3, 1, 8, "c", req=20.0)]
    e = Engine(jobs, FixedController(SJF()), estimator=RequestedTimeEstimator("requested"),
               cs_cost=0, check_interval=10 ** 9).run()
    finish = {j.pid: j.finish for j in e.done}
    assert finish[3] < finish[2]


def test_last2_averages_the_users_last_two_jobs():
    est = Last2Estimator(default=8)
    seq = []
    for burst in [10, 20, 40]:
        j = Job(len(seq) + 1, 0, burst, "u")
        j.est = est.estimate(j)
        seq.append(j.est)
        est.observe(j)
    assert seq == [8, 10, 15]                                  # default, last one, avg of last two
    assert est.estimate(Job(9, 0, 5, "u")) == 30.0             # (20 + 40) / 2: only the last TWO count
    assert est.estimate(Job(10, 0, 5, "other")) == 8           # unseen user -> default


def test_last2_first_job_uses_the_request_when_available():
    est = Last2Estimator(default=8)
    assert est.estimate(Job(1, 0, 5, "new", req=77.0)) == 77.0


def _feed(est, rows, cls="u"):
    for arr, burst in rows:
        j = Job(len(est.terminated.get(cls, [])) + 1, arr, burst, cls)
        j.est = est.estimate(j)
        est.observe(j)


def test_tsafrir_averages_the_two_most_recently_submitted_finished_jobs():
    est = TsafrirEstimator()
    _feed(est, [(0, 10), (5, 20), (9, 40)])
    assert est.estimate(Job(9, 50, 5, "u")) == 30.0                     # (20 + 40) / 2
    assert TsafrirEstimator(window=1).window == 1


def test_tsafrir_window_size_changes_the_guess():
    rows = [(0, 10), (5, 20), (9, 40)]
    for k, expected in [(1, 40.0), (2, 30.0), (3, 70 / 3)]:
        est = TsafrirEstimator(window=k)
        _feed(est, rows)
        assert abs(est.estimate(Job(9, 50, 5, "u")) - expected) < 1e-9, k


def test_tsafrir_uses_submission_order_not_completion_order():
    # job submitted at 0 is long and FINISHES LAST; the paper still uses the two latest SUBMITTED jobs
    est = TsafrirEstimator()
    for arr, burst in [(5, 10), (6, 20), (0, 100)]:                      # completion order: 5, 6, 0
        j = Job(arr + 1, arr, burst, "u")
        j.est = 1.0
        est.observe(j)
    assert est.estimate(Job(9, 50, 5, "u")) == 15.0                      # (10 + 20) / 2, not (20 + 100) / 2
    last2 = Last2Estimator()
    for arr, burst in [(5, 10), (6, 20), (0, 100)]:
        j = Job(arr + 1, arr, burst, "u"); j.est = 1.0; last2.observe(j)
    assert last2.estimate(Job(9, 50, 5, "u")) == 60.0                    # completion-order variant differs


def test_tsafrir_first_job_falls_back_to_the_estimate_then_to_the_default():
    est = TsafrirEstimator(default=8)
    assert est.estimate(Job(1, 0, 5, "new", req=77.0)) == 77.0
    assert est.estimate(Job(2, 0, 5, "new")) == 8


def test_tsafrir_never_exceeds_the_users_estimate():
    est = TsafrirEstimator()
    _feed(est, [(0, 100), (5, 100)])
    assert est.estimate(Job(9, 50, 5, "u", req=30.0)) == 30.0            # discard prediction, use estimate
    assert est.estimate(Job(10, 50, 5, "u", req=500.0)) == 100.0         # request is larger: prediction stays
    nocap = TsafrirEstimator(cap_at_request=False)
    _feed(nocap, [(0, 100), (5, 100)])
    assert nocap.estimate(Job(9, 50, 5, "u", req=30.0)) == 100.0


def test_tsafrir_can_ignore_requested_times_for_ablation():
    est = TsafrirEstimator(use_request=False, default=8)
    assert est.estimate(Job(1, 0, 5, "new", req=77.0)) == 8              # first job: default, request ignored
    _feed(est, [(0, 100), (5, 100)])
    assert est.estimate(Job(9, 50, 5, "u", req=30.0)) == 100.0           # no cap either


def test_tsafrir_rejects_a_bad_window_and_make_estimator_knows_the_new_modes():
    try:
        TsafrirEstimator(window=0)
        raise AssertionError("expected ValueError")
    except ValueError:
        pass
    assert make_estimator("tsafrir").window == 2 and make_estimator("tsafrir-k5").window == 5
    assert make_estimator("tsafrir-nocap").cap is False
    try:
        make_estimator("nonsense")
        raise AssertionError("expected ValueError")
    except ValueError:
        pass


def test_rescale_and_fresh_keep_the_request():
    jobs = [Job(i, i * 10, 5, "a", req=33.0) for i in range(1, 6)]
    assert all(j.req == 33.0 for j in rescale_load(jobs, 0.5))
    assert jobs[0].fresh().req == 33.0


def test_compare_accepts_each_estimator_and_history_is_unchanged():
    jobs = [Job(i, i * 3, 4 + (i % 5) * 3, f"u{i % 3}", req=float(10 + 5 * (i % 4))) for i in range(1, 40)]
    base = compare(jobs, Settings(estimator="history"), include_cheating_reference=False)
    assert abs(base["SJF"].metrics()["avg_wait"] -
               compare(jobs, Settings(), include_cheating_reference=False)["SJF"].metrics()["avg_wait"]) < 1e-12
    for mode in ("last2", "tsafrir", "tsafrir-k5", "requested", "corrected"):
        out = compare(jobs, Settings(estimator=mode), only=["SJF", "Shadow (adaptive)"])
        assert set(out) == {"SJF", "Shadow (adaptive)"} and all(len(e.done) == len(jobs) for e in out.values())
    assert isinstance(make_estimator("history"), BurstEstimator)


if __name__ == "__main__":
    tests = [(k, v) for k, v in sorted(globals().items()) if k.startswith("test_")]
    for name, fn in tests:
        fn()
        print("PASS ", name)
    print(f"\nAll {len(tests)} tests passed.")
