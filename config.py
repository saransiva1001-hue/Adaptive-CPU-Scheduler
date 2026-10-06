"""
Central configuration for the adaptive scheduler.

Every threshold used by the classifier/router lives here so that it can be
tuned (see experiments.py -> threshold sensitivity) and cited in the report.
"""
from dataclasses import dataclass


@dataclass(frozen=True)
class Config:
    # ---- Simulation / cost model ----
    context_switch_cost: float = 0.5      # time units lost on every real context switch
    fixed_rr_quantum: int = 2             # quantum used by the *baseline* Round Robin
    aging_rate: float = 0.1               # priority points gained per time unit waited (adaptive Priority)
    starvation_overtakes: int = 3         # starved = overtaken by >= this many later arrivals ...
    starvation_wait_factor: float = 2.0   # ... AND waiting >= this x the mean waiting time

    # ---- Workload-signature thresholds (initial values, tuned in experiments) ----
    short_burst_limit: float = 4          # burst <= this counts as "short"
    cpu_intensive_avg_burst: float = 8    # avg burst above this -> CPU-intensive
    interactive_short_ratio: float = 0.7  # share of short bursts needed for "interactive"
    interactive_min_density: float = 0.4  # arrival density needed for "interactive"
    high_variability_cv: float = 0.8      # std/mean above this -> variable-burst
    rr_quantum_fraction: float = 0.3      # adaptive RR quantum = max(2, this x average burst)

    # ---- Objective profile ----
    # "balanced"   : minimise waiting/turnaround + tail latency (batch-style goal)
    # "responsive" : response time weighs 4x (interactive/time-sharing goal)
    objective: str = "balanced"
    honour_priorities: bool = False       # True: use Priority+Aging for mixed workloads with >=3 priority levels


DEFAULT_CONFIG = Config()
