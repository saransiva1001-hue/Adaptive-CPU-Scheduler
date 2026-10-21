"""Scheduling rules ("policies"). A policy only answers: who runs next, and for how long?"""


class Policy:
    name = "base"
    quantum = None            # None = runs until finished (non-preemptive)
    uses_estimates = False    # True if the rule depends on burst guesses

    def choose(self, ready, current, slice_ticks):
        raise NotImplementedError

    def max_run(self, job, slice_ticks):
        return job.remaining


class FCFS(Policy):
    name = "FCFS"

    def choose(self, ready, current, slice_ticks):
        if current is not None:
            return current
        return min(ready, key=lambda j: (j.arrival, j.pid))


class SJF(Policy):
    """Shortest Job First (non-preemptive).
    use_true=False -> uses honest estimates (realistic).
    use_true=True  -> cheats with real bursts (reference only, called SJF*)."""

    def __init__(self, use_true=False):
        self.use_true = use_true
        self.name = "SJF*" if use_true else "SJF"
        self.uses_estimates = not use_true

    def _key(self, j):
        v = j.burst if self.use_true else (j.est if j.est is not None else j.burst)
        return (v, j.arrival, j.pid)

    def choose(self, ready, current, slice_ticks):
        if current is not None:
            return current
        return min(ready, key=self._key)


class RoundRobin(Policy):
    def __init__(self, q=4):
        self.q = q
        self.quantum = q
        self.name = f"RR{q}"

    def choose(self, ready, current, slice_ticks):
        if current is not None and slice_ticks < self.q:
            return current
        for j in ready:                 # ready list is kept in queue order
            if j is not current:
                return j
        return current                  # alone: keeps the CPU

    def max_run(self, job, slice_ticks):
        return min(job.remaining, self.q - slice_ticks)
