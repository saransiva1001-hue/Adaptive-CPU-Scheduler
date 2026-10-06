class Process:
    """A single process in the simulation."""

    def __init__(self, pid, arrival_time, burst_time, priority=1):
        if burst_time <= 0:
            raise ValueError(f"P{pid}: burst_time must be > 0")
        if arrival_time < 0:
            raise ValueError(f"P{pid}: arrival_time must be >= 0")
        self.pid = pid
        self.arrival_time = arrival_time
        self.burst_time = burst_time
        self.priority = priority          # lower number = higher priority

        # Filled in by the schedulers / metrics
        self.remaining_time = burst_time
        self.start_time = -1              # first time the process gets the CPU
        self.completion_time = 0
        self.waiting_time = 0             # turnaround - burst
        self.turnaround_time = 0          # completion - arrival
        self.response_time = -1            # start - arrival

    def fresh_copy(self):
        """Return an un-run copy so every algorithm starts from identical input."""
        return Process(self.pid, self.arrival_time, self.burst_time, self.priority)

    def __repr__(self):
        return f"P{self.pid}(Arr:{self.arrival_time}, Burst:{self.burst_time}, Pri:{self.priority})"
