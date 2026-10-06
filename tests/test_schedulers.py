"""Correctness tests against well-known textbook results. Run: python -m tests.test_schedulers"""
import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from core.process import Process
from core.schedulers import fcfs, sjf, round_robin, priority_scheduling
from evaluation.metrics import calculate_metrics


def approx(a, b, tol=1e-6):
    return abs(a - b) < tol


def classic():  # Silberschatz example: P1=24, P2=3, P3=3, all at t=0
    return [Process(1, 0, 24), Process(2, 0, 3), Process(3, 0, 3)]


def test_fcfs():
    m = calculate_metrics(fcfs(classic()))
    assert approx(m["avg_waiting_time"], 17.0)
    assert approx(m["avg_response_time"], 17.0)


def test_sjf():
    m = calculate_metrics(sjf(classic()))
    assert approx(m["avg_waiting_time"], 3.0)


def test_round_robin():
    r = round_robin(classic(), time_quantum=4)
    m = calculate_metrics(r)
    assert approx(m["avg_waiting_time"], 17 / 3)       # 5.666...
    assert approx(m["avg_response_time"], (0 + 4 + 7) / 3)


def test_priority():
    w = [Process(1, 0, 10, 3), Process(2, 0, 1, 1), Process(3, 0, 2, 4), Process(4, 0, 1, 5), Process(5, 0, 5, 2)]
    r = priority_scheduling(w)
    assert [p.pid for p in r.processes] == [2, 5, 1, 3, 4]
    assert approx(calculate_metrics(r)["avg_waiting_time"], 8.2)   # textbook value


def test_single_process_no_switches():
    r = round_robin([Process(1, 0, 10)], time_quantum=2)
    assert r.context_switches == 0 and len(r.timeline) == 1


def test_switch_cost_applied():
    r = fcfs([Process(1, 0, 4), Process(2, 0, 4)], cs_cost=1.0)
    assert r.context_switches == 1 and approx(r.makespan, 9.0)


def test_idle_gap():
    r = fcfs([Process(1, 0, 2), Process(2, 10, 2)])
    assert approx(r.makespan, 12.0)


def test_starvation_detection_sjf():
    # Long job at t=0 is overtaken by a stream of later short jobs under SJF-like ordering
    w = [Process(1, 0, 3), Process(2, 1, 9)] + [Process(10 + i, 2 + i, 1) for i in range(5)]
    m = calculate_metrics(sjf(w))
    assert m["starved_processes"] >= 1


def test_aging_prevents_starvation():
    w = [Process(1, 0, 1, 1), Process(2, 0, 5, 9)] + [Process(10 + i, 1 + 2 * i, 2, 1) for i in range(8)]
    plain = calculate_metrics(priority_scheduling(w))
    aged = calculate_metrics(priority_scheduling(w, aging_rate=1.0))
    assert aged["max_waiting_time"] < plain["max_waiting_time"]


if __name__ == "__main__":
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    for t in tests:
        t(); print(f"PASS  {t.__name__}")
    print(f"\nAll {len(tests)} tests passed.")
