# Adaptive CPU Scheduler v2: shadow-replay policy selection

A Python simulation that chooses between classic scheduling rules (FCFS, SJF, Round Robin)
**while running**, by replaying recent history under each rule (a "trial run") and switching
only when another rule clearly does better. SJF uses **honest burst estimates**, not the true
burst times.

## Quick start

```bash
pip install -r requirements.txt
python -m tests.test_all                         # 13 tests, incl. 150 random fuzz cases
python -m tests.test_loaders                     # 10 tests for CSV/SWF loading
python -m tests.test_estimators                  # 17 tests for the burst estimators
python demo.py                                   # watch it switch rules on one workload
streamlit run app.py                             # the UI: try your own workloads
python -m experiments.run_experiments --runs 100 # full comparison -> ./results
python -m experiments.tune_on_dev_seeds          # how the settings were chosen (seeds 1000+)
python -m experiments.run_real_trace LOG.swf.gz --slices 15 --jobs 200 --load 0.9      # real traces
python -m experiments.run_estimator_study LOG.swf.gz --slices 30 --jobs 200 --load 0.9 # estimator study
#   (for a log without requested times add:  --modes history last2)
python -m experiments.run_warm_study LOG.swf.gz --slices 30 --warm 0 1000        # cold vs warm start, window sizes
python -m experiments.run_estimator_ablation LOG.swf.gz --slices 30             # where does the gain come from?
```

## Using your own workloads (UI)

```bash
streamlit run app.py
```
Pick a source in the sidebar:

* **Generated**: any of the six built-in workload types and a seed.
* **Upload CSV**: columns `arrival, burst` (optional `class`, `pid`). See `examples/sample_workload.csv`.
  Decimals are rounded up to whole ticks.
* **Upload real trace (SWF)**: a Standard Workload Format file from the Parallel Workloads Archive
  (https://www.cs.huji.ac.il/labs/parallel/workload/). Run time becomes the burst and the user id
  becomes the job class (so the estimator learns per user). `examples/sample_trace.swf` is a tiny
  MADE-UP file that only tests the converter; download a real log for real experiments.
  Real jobs ran on many processors; treating each as one burst on one CPU is a simplification.
* Optional: rescale arrival gaps to a target load (real traces are often too idle or overloaded).

The UI shows all methods side by side, a timeline of which rule the adaptive scheduler used,
and sliders for every setting. One run is one sample: for conclusions use many seeds
(`experiments/run_experiments.py`) or many trace slices (use the "Skip first N jobs" box).

## Project layout

| File | What it does |
|---|---|
| `scheduler/job.py` | One CPU job (true burst hidden from the scheduler, `est` = its guess) |
| `scheduler/estimator.py` | Burst guesses: per-class history (textbook), last-two-jobs average (Tsafrir-style), or the user-requested runtime (raw or corrected by a learned ratio) |
| `scheduler/policies.py` | FCFS, SJF (estimates; `SJF*` = cheating reference), Round Robin |
| `scheduler/engine.py` | Simulator; the active rule can change mid-run; charges context-switch and rule-change costs |
| `scheduler/controllers.py` | `FixedController`, `RuleController` (old if/else design), `ShadowController` (new) |
| `scheduler/workloads.py` | Six workload types incl. phase-changing and "spiky" (unpredictable) ones |
| `scheduler/loaders.py` | Load your own CSV or a real SWF trace; rescale load |
| `scheduler/compare.py` | Run every method on one workload (used by the UI) |
| `app.py` | Streamlit UI |
| `examples/` | A sample CSV and a tiny made-up SWF file |
| `experiments/run_experiments.py` | All methods x all workloads x N seeds, paired stats, plots |
| `experiments/tune_on_dev_seeds.py` | Settings chosen on separate dev seeds, never the reported ones |
| `experiments/run_real_trace.py` | Many slices of real SWF logs, rescaled to a target load |
| `experiments/run_estimator_study.py` | History vs requested vs corrected burst estimates on a real log |
| `results/`, `results_real/`, `results_estimators/`, `results_estimators_paragon/` | Output of the experiment scripts |

## The three ideas, and what actually happened (100 seeds per workload)

**A. Trial run before switching (shadow replay): partly supported.**
Mean waiting time (ticks, lower is better):

| workload | FCFS | SJF | RR4 | Old rule router | **Shadow** |
|---|---|---|---|---|---|
| interactive | 16.5 | **14.2** | 24.6 | 14.2 | 14.3 |
| batch | 43.8 | **39.6** | 153.7 | 44.3 | 39.9 |
| mixed | 39.0 | **26.2** | 68.5 | 34.8 | 27.6 |
| phased | 32.6 | **20.8** | 63.8 | 24.5 | 21.1 |
| phased_mix | 66.2 | 46.7 | 75.8 | 56.2 | **45.4** |
| spiky | 60.4 | 52.2 | **35.0** | 51.6 | 41.7 |

Regret = % worse than the best single fixed rule picked in hindsight, per run:

| method | mean regret | worst workload |
|---|---|---|
| FCFS | 38.6% | 77.4% |
| SJF | 11.8% | 60.4% |
| RR4 | 143.8% | 295.5% |
| Old rule router | 23.7% | 63.5% |
| **Shadow** | **8.2%** | **30.2%** |

* Shadow does **not** beat always-SJF on average wait in most workloads. It is slightly worse
  there (by 0.03 to 1.4 ticks, 95% CIs exclude zero in 4 of 6). It is clearly better on
  `spiky` (-10.5 ticks, CI [-15.9, -5.7]), and not clearly different on `phased_mix`.
* Its real strength is **robustness**: it has no catastrophic workload. The worst-case regret
  is half of SJF's and far below RR's, and it needed no knowledge of the workload type.
* The old if/else design was worse than always-SJF (23.7% vs 11.8% mean regret).
* Cost: about 1 rule change per run; about 12 ms of controller time per run in this Python
  simulation (vs 0.01 ms for a fixed rule). This is simulator wall-clock, not kernel cost.

**B. Honest burst estimates + a reliability guard: estimates yes, guard no.**
Using real estimates is what makes the setting realistic (`SJF*`, which cheats with true
bursts, is 10-30% better than SJF depending on the workload, which shows how much perfect knowledge of burst times would be worth).
The reactive "distrust SJF when recent guesses were bad" guard did **not** help at any
threshold on dev seeds, and made things worse on `mixed` and `phased_mix`. The replay
already sees how badly SJF's guesses performed. Report this as a negative result.

**C. Requirement-driven choice (p95 wait <= limit): inconsistent.**
See `results/requirement.md`. It lowered the violation rate on `batch` (SJF 41% -> 28%) but
FCFS alone did better (22%), and it did **worse** than SJF on `phased` (43% vs 37%). The
short replay window is a weak predictor of the whole-run p95. Do not claim this works.

**Phase changes were not the key.** I expected phase-changing workloads to favour adaptation.
They don't: SJF is already best in both the interactive and batch phases, so Shadow rarely
switches on `phased`. Adaptation pays off when the *estimates become unreliable* (`spiky`).

## Real traces (SDSC SP2 and SDSC Paragon, 15 slices x 200 jobs, load 0.9)

Average wait in ticks (lower is better). Controller check interval = 0.5 x mean burst (10 ticks is
far too frequent for jobs thousands of ticks long). No tuning on these logs.

| Method | SP2 | Paragon |
|---|---|---|
| FCFS | 4,940 | 61,110 |
| SJF (history guesses) | 2,200 | 37,966 |
| RR4 | 2,414 | **18,515** |
| Old rule router | 2,499 | 42,023 |
| **Shadow** | **2,173** | 32,280 |
| SJF* (cheats) | 1,007 | 13,353 |

Shadow is tied with SJF on SP2 and beats SJF on Paragon, but does not beat RR4 on Paragon. It is
never the worst, but it is not the best either. See `results_real/real_summary.md`.

## Better burst estimates (what we found, including a correction)

Estimators: `history` (running average, fixed default of 8 for a user's first job), `last2` (average of
the last two finished jobs), `tsafrir` (the published predictor, see below), `requested` (the runtime the
user asked for) and `corrected` (request x the user's learned actual/requested ratio).

**The published predictor** (Tsafrir, Etsion & Feitelson, TPDS 2007, Sec. 3.1), implemented as
`TsafrirEstimator`: (1) guess = average runtime of the user's two most recently *submitted* jobs that have
already *finished*; (2) a user with no such jobs: use the user's estimate (the request); (3) never guess more
than the user's own estimate. The paper also "corrects" predictions that turn out too short; that exists for
backfilling reservations, so it changes nothing for our single-CPU, non-preemptive SJF and is not implemented.

| Question | Evidence (SP2, SJF, average wait in ticks) | Verdict |
|---|---|---|
| Does the estimator matter at all? | Perfect knowledge (SJF*) is far better than any guess | Yes, a large gap remains |
| Where did the big early gain come from? | Cold-start slices: old running average 2,119; the **same** running average but using the request for a user's first job 1,442; last-2 with no requests 2,244; full Tsafrir 1,394 | Mostly **the request fallback**, not the last-two averaging (`results_last_k/sp2_ablation.md`) |
| Is last-two better than a running average once history exists? | Warm start (1,000 earlier jobs): running average 931, Tsafrir k=2 864 (difference -67, CI -176 to 14) | **No clear difference** (`results_last_k/sp2_warm_vs_cold.md`) |
| Does window size matter (1, 2, 3, 5, 10)? | 879 / 864 / 853 / 865 / 864, all within noise | No. The paper's "smaller window is better" is not reproduced here |
| Does the correction help? | `corrected` 772 vs Tsafrir 864 (difference -93, CI -137 to -48), 17% better than the running average | **Yes, clearly** |
| Paragon (no requests)? | Running average 13,818, Tsafrir k=2 14,233, k=1 17,658 (clearly worse), k=10 13,765 | Last-two is not special; one job is too noisy |
| Does always-SJF still beat Shadow with good guesses? | Warm: SJF 765 vs Shadow 954 (corrected); 880 vs 1,122 (Tsafrir); 914 vs 1,115 (running average) | **Yes** for all three (`results_last_k/sp2_warm_shadow_vs_sjf.md`) |

**Correction of an earlier claim.** We first reported that a last-two predictor made SJF 33% better than the
running average. That number came from 200-job slices that each started with *empty history*, so most guesses
were first-job guesses, and the old estimator guessed a fixed 8 for them. The gain was the request fallback, not
the averaging rule. Our old running average (weight 0.5 on the last job, 0.25 on the one before...) is itself a
"recent jobs matter most" rule, which is why it matches last-two once history exists.
Scripts: `run_estimator_ablation.py`, `run_warm_study.py`, `run_warm_shadow.py`, `run_last_k_study.py`.

## Related work: what is NOT new here

I searched the literature (abstracts and summaries only; read the papers before citing them).

* **Shadow replay = simulation-driven portfolio scheduling.** A portfolio scheduler holds several policies and
  periodically picks the one expected to do best; the simulation-driven variant runs an online simulation of
  each candidate. Documented problems: simulating every candidate is costly, and selections can be poor when a
  policy's performance is hard to predict (matches our heavy-tailed Paragon result).
  - Portfolio scheduling for scientific workloads, SC13: https://sc13.supercomputing.org/schedule/event_detail.php-evid=pap326.html
  - Simulation-driven portfolio scheduling in workflow systems: https://par.nsf.gov/servlets/purl/10525449
  - AtLarge overview (portfolio schedulers, section 6.6): https://arxiv.org/pdf/1902.05416
* **Learned policy selectors.** Sant'Ana et al., "Real-Time Scheduling Policy Selection from Queue and Machine
  States", CCGrid 2019 (logistic regression / SVM over 8 policies): https://bv.fapesp.br/en/publicacao/225395 ;
  Mixture-of-Schedulers / Adaptive Scheduling Agent (Linux sched_ext), 2025: https://arxiv.org/abs/2511.11628
* **Runtime estimation.** Tsafrir, Etsion & Feitelson, "Backfilling Using System-Generated Predictions Rather
  than User Runtime Estimates", TPDS 2007: https://www.cse.huji.ac.il/~feit/papers/Pred07TPDS.pdf ;
  Gaussier et al., "Improving Backfilling by using Machine Learning to predict Running Times", SC15:
  https://hal.archives-ouvertes.fr/hal-01221186
* **What remains:** a small reproducible single-CPU study with regret and paired statistics on real SDSC
  logs; replay decisions made with the same noisy estimates the scheduler really has; and the findings that
  estimation mattered more than switching and that always-SJF beats switching once guesses are good.
  Do not call the idea novel; call it a careful evaluation.

## What you can honestly claim

> "We built a simulator where the scheduler uses realistic burst estimates and can change
> rule mid-run. On synthetic workloads, a shadow-replay selector keeps worst-case regret to ~30%
> (SJF: 60%, RR: 296%) without knowing the workload type, and beats SJF when burst guesses are
> unreliable; it does not beat always-SJF on predictable workloads. On real SDSC traces it is
> never the worst but not the best either. The largest gain came from better burst estimates, mainly
> from using the user's requested runtime (for first jobs, and corrected by a learned ratio, about 17%
> better than a running average once history exists), not from the last-two averaging rule itself.
> With good estimates always-SJF beat adaptive switching. A reliability guard and a p95-requirement mode did not
> give reliable gains."

## Limitations (say these in the report)

* Synthetic workloads are from our own generators, and `spiky` is *designed* to break estimation.
* Real-trace tests use two logs (one has requested times); each parallel job is treated as one burst
  on a single CPU, and arrivals are rescaled to a target load. Test more logs before generalising.
* Each job is a single CPU burst; SJF is non-preemptive; no SRTF/MLFQ/priorities/I/O.
* The replay window is the last 12 arrivals, so older queued jobs are not represented.
* Only a handful of settings were tuned (on dev seeds 1000-1019); more tuning could change rankings.
* Costs are modelled as ticks (context switch = 1, rule change = 1), not measured on hardware.
* Novelty: runtime policy selection from a portfolio exists in the literature (HPC job
  scheduling, learned expert-routing). Your contributions here are the honest-estimate setting,
  replay-based (not predictor-based) selection, and the regret/robustness evaluation with
  negative results. Do a proper literature search before using the word "novel".
