def calculate_metrics(result, starvation_overtakes=3, starvation_wait_factor=2.0):
    """Compute all performance metrics from a ScheduleResult."""
    procs = result.processes
    n = len(procs)
    if n == 0:
        return {}

    for p in procs:
        p.turnaround_time = p.completion_time - p.arrival_time
        p.waiting_time = p.turnaround_time - p.burst_time
        p.response_time = p.start_time - p.arrival_time      # FIX: was never computed before

    first_arrival = min(p.arrival_time for p in procs)
    span = result.makespan - first_arrival

    # Starvation: a process is "starved" if it is (a) overtaken by >= K processes that
    # arrived AFTER it and (b) its wait is an outlier (>= factor x the mean wait).
    # Being bypassed alone is just normal SJF/priority behaviour; (b) makes it a real tail-latency problem.
    waits = [p.waiting_time for p in procs]
    mean_wait = sum(waits) / n
    starved = 0
    for p in procs:
        overtaken = sum(1 for q in procs
                        if q.arrival_time > p.arrival_time and q.completion_time < p.completion_time)
        if overtaken >= starvation_overtakes and p.waiting_time >= starvation_wait_factor * max(mean_wait, 1e-9):
            starved += 1

    return {
        "avg_waiting_time": sum(waits) / n,
        "avg_turnaround_time": sum(p.turnaround_time for p in procs) / n,
        "avg_response_time": sum(p.response_time for p in procs) / n,
        "max_waiting_time": max(waits),
        "throughput": n / span if span > 0 else 0.0,
        "cpu_utilization": result.busy_time / span if span > 0 else 0.0,
        "context_switches": result.context_switches,
        "switch_overhead": result.switch_overhead,
        "starved_processes": starved,
    }
