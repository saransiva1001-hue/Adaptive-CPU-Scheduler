"""A single CPU job (one CPU burst) in the simulation."""
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class Job:
    pid: int
    arrival: int
    burst: int                      # TRUE burst. A real scheduler never sees this in advance.
    cls: str = "default"            # program class; the estimator learns per class
    est: Optional[float] = None     # estimated burst, fixed when the job arrives
    req: Optional[float] = None     # runtime the USER asked for (SWF field 9), if the trace has it
    remaining: int = field(init=False)
    start: int = field(default=-1, init=False)
    finish: int = field(default=-1, init=False)

    def __post_init__(self):
        if self.burst <= 0:
            raise ValueError("burst must be positive")
        self.remaining = self.burst

    @property
    def served(self) -> int:
        return self.burst - self.remaining

    @property
    def turnaround(self) -> int:
        return self.finish - self.arrival

    @property
    def wait(self) -> int:
        return self.turnaround - self.burst

    @property
    def response(self) -> int:
        return self.start - self.arrival

    def fresh(self, burst=None, arrival=None, keep_est=True) -> "Job":
        """Un-run copy of this job (optionally with different burst/arrival)."""
        return Job(self.pid,
                   self.arrival if arrival is None else arrival,
                   self.burst if burst is None else burst,
                   self.cls,
                   self.est if keep_est else None,
                   req=self.req)
