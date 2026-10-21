"""Watch the shadow-replay scheduler on a phase-changing workload.

    python demo.py [workload] [seed]        e.g.  python demo.py phased_mix 6

The default seed was picked because it shows switching clearly. It is NOT typical:
see results/summary.md for averages over 100 seeds (the honest picture).
"""
import sys

from experiments.run_experiments import CHECK, CS, SWITCH_PENALTY
from scheduler.controllers import FixedController, ShadowController
from scheduler.engine import Engine
from scheduler.policies import FCFS, RoundRobin, SJF
from scheduler.workloads import PHASES, WORKLOADS, generate, offered_load

name = sys.argv[1] if len(sys.argv) > 1 else "phased_mix"
seed = int(sys.argv[2]) if len(sys.argv) > 2 else 6
jobs = generate(name, seed)
print(f"workload '{name}' (seed {seed}): {len(jobs)} jobs, offered load {offered_load(jobs):.2f}")
print("phases:", " -> ".join(f"{p}({t} ticks)" for p, t in WORKLOADS[name]), "\n")

def run(ctrl):
    return Engine(jobs, ctrl, cs_cost=CS, switch_penalty=SWITCH_PENALTY, check_interval=CHECK).run()

pol = [FCFS(), SJF(), RoundRobin(4)]
results = {p.name: run(FixedController(p)) for p in pol}
shadow = run(ShadowController(pol, initial=pol[1]))
results["Shadow (adaptive)"] = shadow

print(f"{'method':20s} {'avg wait':>9s} {'p95 wait':>9s} {'max wait':>9s} {'ctx sw':>7s}")
for k, e in results.items():
    m = e.metrics()
    print(f"{k:20s} {m['avg_wait']:9.1f} {m['p95_wait']:9.1f} {m['max_wait']:9.1f} {m['ctx_switches']:7d}")

print("\nWhen the shadow scheduler changed its rule:")
if not shadow.switch_log:
    print("  (never - it started on SJF and no trial run beat it by >= 5% twice in a row)")
for t, old, new in shadow.switch_log:
    print(f"  t={t:5d}: {old} -> {new}")
