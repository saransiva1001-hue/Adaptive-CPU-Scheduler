import math


def percentile(values, p):
    """Nearest-rank percentile."""
    if not values:
        return 0.0
    s = sorted(values)
    return float(s[max(0, math.ceil(p / 100 * len(s)) - 1)])


def metrics_from_jobs(jobs):
    """Metrics that only need finished jobs (also used inside shadow replays)."""
    n = len(jobs)
    waits = [j.wait for j in jobs]
    return {
        "avg_wait": sum(waits) / n,
        "p95_wait": percentile(waits, 95),
        "max_wait": float(max(waits)),
        "avg_turnaround": sum(j.turnaround for j in jobs) / n,
        "avg_response": sum(j.response for j in jobs) / n,
    }


def full_metrics(engine):
    m = metrics_from_jobs(engine.done)
    makespan = max(j.finish for j in engine.done)
    m.update({
        "ctx_switches": engine.ctx_switches,
        "policy_switches": len(engine.switch_log),
        "makespan": makespan,
        "utilisation": engine.busy / makespan if makespan else 0.0,
        "controller_ms": engine.control_seconds * 1000,
    })
    return m
