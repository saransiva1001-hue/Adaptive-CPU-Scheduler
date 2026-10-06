"""
Baseline CPU scheduling algorithms, all built on one small CPU model so that
context-switch counting, switch cost and the Gantt timeline are identical
for every policy (fair comparison).
"""
from dataclasses import dataclass


@dataclass
class ScheduleResult:
    processes: list          # finished processes, in completion order
    context_switches: int    # real switches: CPU moved from one process to a *different* one
    timeline: list           # Gantt data: (pid, start, end)
    makespan: float          # time at which the last process finished
    busy_time: float         # time spent executing process code
    switch_overhead: float   # time lost to context switching


class _CPU:
    """Tiny CPU model: tracks time, switches, overhead and the Gantt timeline."""

    def __init__(self, cs_cost):
        self.t = 0.0
        self.cs_cost = cs_cost
        self.last_pid = None
        self.switches = 0
        self.busy = 0.0
        self.overhead = 0.0
        self.timeline = []

    def idle_until(self, t):
        if t > self.t:
            self.t = t

    def run(self, p, duration):
        # A switch only happens when the CPU changes to a *different* process.
        if self.last_pid is not None and self.last_pid != p.pid:
            self.switches += 1
            self.t += self.cs_cost
            self.overhead += self.cs_cost
        start = self.t
        if p.start_time == -1:
            p.start_time = start
        self.t += duration
        self.busy += duration
        p.remaining_time -= duration
        if self.timeline and self.timeline[-1][0] == p.pid and self.timeline[-1][2] == start:
            self.timeline[-1] = (p.pid, self.timeline[-1][1], self.t)
        else:
            self.timeline.append((p.pid, start, self.t))
        self.last_pid = p.pid
        if p.remaining_time <= 1e-9:
            p.remaining_time = 0
            p.completion_time = self.t

    def result(self, completed):
        return ScheduleResult(completed, self.switches, self.timeline,
                              self.t, self.busy, self.overhead)


def _clone(process_list):
    return [p.fresh_copy() for p in process_list]


def _non_preemptive(process_list, key_fn, cs_cost):
    """Generic non-preemptive scheduler: at each decision point run the ready
    process with the smallest key_fn(p, now)."""
    pending = sorted(_clone(process_list), key=lambda p: (p.arrival_time, p.pid))
    cpu = _CPU(cs_cost)
    completed = []
    while pending:
        ready = [p for p in pending if p.arrival_time <= cpu.t]
        if not ready:
            cpu.idle_until(min(p.arrival_time for p in pending))
            continue
        p = min(ready, key=lambda q: key_fn(q, cpu.t))
        cpu.run(p, p.burst_time)
        pending.remove(p)
        completed.append(p)
    return cpu.result(completed)


def fcfs(process_list, cs_cost=0.0):
    """First-Come First-Served (non-preemptive)."""
    return _non_preemptive(process_list, lambda p, now: (p.arrival_time, p.pid), cs_cost)


def sjf(process_list, cs_cost=0.0, aging_rate=0.0):
    """Shortest Job First (non-preemptive). aging_rate > 0 gives 'SJF with aging':
    a waiting job's effective burst shrinks over time so long jobs cannot be bypassed forever."""
    def key(p, now):
        return (p.burst_time - aging_rate * (now - p.arrival_time), p.arrival_time, p.pid)
    return _non_preemptive(process_list, key, cs_cost)


def priority_scheduling(process_list, cs_cost=0.0, aging_rate=0.0):
    """Priority scheduling (non-preemptive, lower number = higher priority).
    aging_rate > 0 lowers a waiting process's effective priority number over
    time, which prevents starvation. aging_rate = 0 gives the plain baseline."""
    def key(p, now):
        return (p.priority - aging_rate * (now - p.arrival_time), p.arrival_time, p.pid)
    return _non_preemptive(process_list, key, cs_cost)


def round_robin(process_list, time_quantum=2, cs_cost=0.0):
    """Round Robin (preemptive). Newly arrived processes are queued before the
    preempted one, the usual textbook convention."""
    if time_quantum <= 0:
        raise ValueError("time_quantum must be > 0")
    procs = sorted(_clone(process_list), key=lambda p: (p.arrival_time, p.pid))
    n = len(procs)
    cpu = _CPU(cs_cost)
    queue, completed, i = [], [], 0
    while len(completed) < n:
        while i < n and procs[i].arrival_time <= cpu.t:
            queue.append(procs[i]); i += 1
        if not queue:
            cpu.idle_until(procs[i].arrival_time)
            continue
        p = queue.pop(0)
        cpu.run(p, min(p.remaining_time, time_quantum))
        while i < n and procs[i].arrival_time <= cpu.t:
            queue.append(procs[i]); i += 1
        if p.remaining_time > 0:
            queue.append(p)
        else:
            completed.append(p)
    return cpu.result(completed)
