"""
Adaptive policy selection:  Workload -> Signature -> Classification -> Policy -> Execution

Two explicit stages (Steps 3 and 4 of the methodology):
  classify_workload(signature) -> label
  select_policy(label, ...)    -> (policy name, runner, human-readable reason)

All thresholds come from config.Config. The two objective profiles exist because the
experiments showed that "best policy" depends on the goal, not only on the workload:
  balanced   -> SJF-family wins (lowest waiting/turnaround), FCFS for long uniform jobs
  responsive -> Round Robin wins whenever long bursts are present (response time 4-8x lower)
"""
from config import DEFAULT_CONFIG
from core.schedulers import fcfs, sjf, round_robin, priority_scheduling


def classify_workload(sig, cfg=DEFAULT_CONFIG):
    """Waterfall of rules; the first matching rule wins."""
    if sig["burst_cv"] >= cfg.high_variability_cv:
        return "variable_burst"      # a few very long jobs among short ones -> convoy risk
    if sig["avg_burst"] > cfg.cpu_intensive_avg_burst:
        return "cpu_intensive"       # long, similar bursts
    if sig["short_burst_ratio"] >= cfg.interactive_short_ratio and sig["arrival_density"] > cfg.interactive_min_density:
        return "interactive"         # many short bursts arriving densely
    if sig["avg_burst"] <= cfg.short_burst_limit:
        return "short_burst"         # short bursts, light arrival rate
    return "mixed"


def rr_quantum(sig, cfg=DEFAULT_CONFIG):
    return max(2, round(cfg.rr_quantum_fraction * sig["avg_burst"]))


def select_policy(label, sig, process_list, cfg=DEFAULT_CONFIG):
    c = cfg.context_switch_cost

    def sjf_aging(reason):
        return ("SJF+Aging", lambda: sjf(process_list, c, aging_rate=0.3), reason)

    short_only = label in ("short_burst", "interactive")

    if cfg.objective == "responsive" and not short_only:
        q = rr_quantum(sig, cfg)
        return (f"Round Robin (q={q})", lambda: round_robin(process_list, q, c),
                f"responsive goal with long bursts present (avg={sig['avg_burst']:.1f}, CV={sig['burst_cv']:.2f}): "
                f"time-slicing keeps response time low; quantum = {cfg.rr_quantum_fraction:g} x avg burst")

    if label == "cpu_intensive":
        return ("FCFS", lambda: fcfs(process_list, c),
                f"avg burst={sig['avg_burst']:.1f}, low variability (CV={sig['burst_cv']:.2f}): SJF gains little; "
                f"FCFS is fair and has the fewest context switches")
    if label == "variable_burst":
        return sjf_aging(f"burst CV={sig['burst_cv']:.2f} is high: shortest-first removes the convoy effect; "
                         f"aging stops long jobs starving")
    if label in ("short_burst", "interactive"):
        return sjf_aging(f"{sig['short_burst_ratio']:.0%} short bursts: shortest-first minimises waiting; "
                         f"time-slicing adds only switch overhead")
    # mixed
    if cfg.honour_priorities and sig["distinct_priorities"] >= 3:
        return ("Priority+Aging", lambda: priority_scheduling(process_list, c, aging_rate=cfg.aging_rate),
                "mixed bursts with several priority levels: honour priorities, aging prevents starvation")
    return sjf_aging("mixed bursts: shortest-first minimises waiting; aging protects long jobs")


def adaptive_scheduler(process_list, sig, cfg=DEFAULT_CONFIG):
    """Returns (ScheduleResult, decision) where decision = {label, policy, reason}."""
    label = classify_workload(sig, cfg)
    policy, run, reason = select_policy(label, sig, process_list, cfg)
    return run(), {"label": label, "policy": policy, "reason": reason}
