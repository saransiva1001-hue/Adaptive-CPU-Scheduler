"""Workload generators. Each workload is a list of PHASES; a phase is a stretch of time
with its own arrival rate and mix of job classes. Phase-changing workloads are where a
single fixed rule is least likely to be best the whole time."""
import random

from .job import Job

CLASS_MEAN = {"edit": 3, "query": 5, "compile": 20, "render": 30}

PHASES = {
    # p = chance a new job arrives in any one tick
    "interactive": dict(p=0.20, mix={"edit": .6, "query": .4}, cv=.25, spike=0.0),
    "batch":       dict(p=0.035, mix={"compile": .6, "render": .4}, cv=.20, spike=0.0),
    "mixed":       dict(p=0.065, mix={"edit": .5, "compile": .3, "render": .2}, cv=.25, spike=0.0),
    # 'spiky': 15% of jobs run 10x longer than their class normally does -> bad guesses
    "spiky":       dict(p=0.050, mix={"edit": .5, "query": .3, "compile": .2}, cv=.25,
                        spike=0.15, spike_mult=10),
}

WORKLOADS = {
    "interactive": [("interactive", 300)],
    "batch":       [("batch", 900)],
    "mixed":       [("mixed", 500)],
    "spiky":       [("spiky", 500)],
    "phased":      [("interactive", 150), ("batch", 450), ("interactive", 150)],
    "phased_mix":  [("batch", 450), ("spiky", 250), ("interactive", 150)],
}


def _burst(rng, mean, cv, spike, spike_mult):
    b = max(1, round(rng.gauss(mean, cv * mean)))
    if spike and rng.random() < spike:
        b = round(b * spike_mult)
    return int(b)


def generate(name, seed):
    rng = random.Random(seed)
    jobs, pid, t = [], 1, 0
    for phase_name, length in WORKLOADS[name]:
        ph = PHASES[phase_name]
        classes, weights = zip(*ph["mix"].items())
        for _ in range(length):
            if rng.random() < ph["p"]:
                cls = rng.choices(classes, weights)[0]
                b = _burst(rng, CLASS_MEAN[cls], ph["cv"], ph["spike"], ph.get("spike_mult", 1))
                jobs.append(Job(pid, t, b, cls))
                pid += 1
            t += 1
    if not jobs:                                  # extremely unlikely, keeps callers safe
        jobs.append(Job(1, 0, 3, "edit"))
    return jobs


def offered_load(jobs):
    span = max(j.arrival for j in jobs) + 1
    return sum(j.burst for j in jobs) / span
