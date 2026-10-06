import math
from config import DEFAULT_CONFIG


def calculate_workload_signature(processes, cfg=DEFAULT_CONFIG):
    """
    Workload signature = measurable characteristics of the processes waiting for the CPU.

    avg_burst          mean CPU burst
    burst_std_dev      spread of bursts
    burst_cv           std/mean, scale-free variability (used by the router)
    short_burst_ratio  share of bursts <= cfg.short_burst_limit (interactivity proxy)
    arrival_density    processes per time unit over the arrival window (n / (span + 1));
                       the +1 avoids divide-by-zero when everything arrives together
    load_factor        total burst demand / arrival window (>1 means work arrives faster
                       than it can be served, i.e. a queue builds up)
    priority_spread    max - min priority value
    distinct_priorities number of different priority levels in use
    """
    if not processes:
        return {}

    n = len(processes)
    bursts = [p.burst_time for p in processes]
    arrivals = [p.arrival_time for p in processes]
    priorities = [p.priority for p in processes]

    avg_burst = sum(bursts) / n
    std = math.sqrt(sum((b - avg_burst) ** 2 for b in bursts) / n)
    window = (max(arrivals) - min(arrivals)) + 1

    return {
        "total_processes": n,
        "avg_burst": avg_burst,
        "burst_std_dev": std,
        "burst_cv": std / avg_burst,
        "short_burst_ratio": sum(1 for b in bursts if b <= cfg.short_burst_limit) / n,
        "arrival_density": n / window,
        "load_factor": sum(bursts) / window,
        "priority_spread": max(priorities) - min(priorities),
        "distinct_priorities": len(set(priorities)),
    }
