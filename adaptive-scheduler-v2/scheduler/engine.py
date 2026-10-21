"""Discrete-time CPU simulator that supports switching policy WHILE running.

Time is in whole ticks. The engine runs "chunks": a job runs until the policy would
next need to make a decision (finish, quantum end) or until the next controller check,
whichever comes first. This is exact for the policies used here and fast enough
to replay recent history many times.
"""
import time as _time

from .estimator import BurstEstimator
from .metrics import full_metrics


class Engine:
    def __init__(self, jobs, controller, estimator="auto", cs_cost=1,
                 switch_penalty=0, check_interval=10):
        self.pending = sorted((j.fresh() for j in jobs), key=lambda j: (j.arrival, j.pid))
        self.controller = controller
        self.estimator = BurstEstimator() if estimator == "auto" else estimator
        self.cs_cost = cs_cost
        self.switch_penalty = switch_penalty
        self.check_interval = check_interval

        self.now = 0
        self.next_check = 0
        self.ready = []          # queue order
        self.admitted = []       # every job that has arrived so far
        self.done = []
        self.current = None
        self.slice_ticks = 0
        self.last_pid = None
        self.ctx_switches = 0
        self.busy = 0
        self.overhead = 0
        self.switch_log = []     # (time, old_policy, new_policy)
        self.control_seconds = 0.0
        self._i = 0
        self.policy = controller.initial_policy()

    # -- helpers ---------------------------------------------------------
    def _admit(self):
        while self._i < len(self.pending) and self.pending[self._i].arrival <= self.now:
            j = self.pending[self._i]
            self._i += 1
            if j.est is None:
                j.est = self.estimator.estimate(j) if self.estimator else float(j.burst)
            self.ready.append(j)
            self.admitted.append(j)

    def _burn_overhead(self, ticks):
        if ticks > 0:
            self.now += ticks
            self.overhead += ticks
            self._admit()

    def _control(self):
        t0 = _time.perf_counter()
        new = self.controller.select(self)
        self.control_seconds += _time.perf_counter() - t0
        if new.name != self.policy.name:
            self.switch_log.append((self.now, self.policy.name, new.name))
            self.policy = new
            self._burn_overhead(self.switch_penalty)
        self.next_check = self.now + self.check_interval

    # -- main loop ---------------------------------------------------------
    def run(self):
        n = len(self.pending)
        while len(self.done) < n:
            self._admit()
            if self.now >= self.next_check:
                self._control()
                self._admit()
            if not self.ready:
                self.now = self.pending[self._i].arrival   # CPU idle: jump ahead
                self.current = None
                continue

            job = self.policy.choose(self.ready, self.current, self.slice_ticks)
            if job is not self.current:
                if self.current is not None and self.current.remaining > 0:
                    self.ready.remove(self.current)        # preempted: back of the queue
                    self.ready.append(self.current)
                self.slice_ticks = 0
            elif self.policy.quantum and self.slice_ticks >= self.policy.quantum:
                self.slice_ticks = 0                       # alone: starts a fresh slice

            if self.last_pid is not None and self.last_pid != job.pid:
                self.ctx_switches += 1
                self._burn_overhead(self.cs_cost)

            if job.start < 0:
                job.start = self.now
            chunk = min(self.policy.max_run(job, self.slice_ticks),
                        max(1, self.next_check - self.now))
            self.now += chunk
            self.busy += chunk
            job.remaining -= chunk
            self.slice_ticks += chunk
            self.last_pid = job.pid
            self.current = job

            if job.remaining == 0:
                job.finish = self.now
                self.ready.remove(job)
                self.done.append(job)
                if self.estimator:
                    self.estimator.observe(job)
                self.current = None
                self.slice_ticks = 0
        return self

    def metrics(self):
        return full_metrics(self)

    # -- history the controller may look at ---------------------------------------
    def recent_jobs(self, k):
        """The last k arrivals as the scheduler honestly knows them: finished jobs
        have their real burst; unfinished ones only have their estimate (or what
        they already used, if more). Arrival times are shifted to start at 0."""
        window = self.admitted[-k:]
        if not window:
            return []
        t0 = min(j.arrival for j in window)
        out = []
        for j in window:
            if j.finish >= 0:
                b = j.burst
            else:
                b = max(int(round(j.est)), j.served + 1, 1)
            out.append(j.fresh(burst=b, arrival=j.arrival - t0, keep_est=True))
        return out
