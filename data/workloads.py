import sys, os, random
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from core.process import Process

# ---- Hand-made benchmark scenarios (used for report tables) ----
BENCHMARK_WORKLOADS = {
    "CPU-Intensive Scenario": [
        Process(1, 0, 10, 2), Process(2, 1, 14, 3), Process(3, 2, 12, 1)],
    "Interactive Scenario": [
        Process(4, 0, 2, 1), Process(5, 1, 1, 2), Process(6, 2, 3, 1), Process(7, 3, 2, 3)],
    "Short-Burst Batch": [
        Process(8, 0, 3, 2), Process(9, 2, 4, 2), Process(10, 4, 2, 1)],
    "Mixed Workload": [
        Process(11, 0, 8, 2), Process(12, 1, 2, 1), Process(13, 3, 12, 3), Process(14, 5, 3, 2)],
}

WORKLOAD_TYPES = ["cpu_intensive", "short_burst", "interactive", "mixed", "high_load", "variable_burst"]


def generate_random_workload(num_processes=8, workload_type="mixed", seed=None):
    """
    Seeded synthetic workload generator for the 6 workload types in the project objectives.
      cpu_intensive  long bursts (10-20), sparse arrivals
      short_burst    short bursts (1-4), sparse arrivals
      interactive    very short bursts (1-3), dense arrivals
      mixed          bursts 1-15, moderate arrivals
      high_load      many processes, moderate bursts, near-simultaneous arrivals
      variable_burst mostly short jobs plus a few very long ones
    """
    rng = random.Random(seed)
    procs, t = [], 0
    for i in range(1, num_processes + 1):
        if workload_type == "cpu_intensive":
            t += rng.randint(0, 3);  burst = rng.randint(10, 20)
        elif workload_type == "short_burst":
            t += rng.randint(2, 5);  burst = rng.randint(1, 4)
        elif workload_type == "interactive":
            t += rng.randint(0, 1);  burst = rng.randint(1, 3)
        elif workload_type == "high_load":
            t += rng.randint(0, 1);  burst = rng.randint(4, 10)
        elif workload_type == "variable_burst":
            t += rng.randint(0, 2);  burst = rng.randint(25, 40) if rng.random() < 0.2 else rng.randint(1, 4)
        else:  # mixed
            t += rng.randint(0, 2);  burst = rng.randint(1, 15)
        procs.append(Process(i, t, burst, rng.randint(1, 5)))
    if workload_type == "high_load":
        procs = procs[:max(num_processes, 12)]
    return procs


if __name__ == "__main__":
    for wt in WORKLOAD_TYPES:
        print(wt, generate_random_workload(5, wt, seed=1))
