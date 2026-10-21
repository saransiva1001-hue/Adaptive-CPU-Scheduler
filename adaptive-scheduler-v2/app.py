"""Streamlit UI.   Run with:   streamlit run app.py"""
import io

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd
import streamlit as st

from scheduler.compare import Settings, compare, policy_segments
from scheduler.loaders import WorkloadError, load_csv, load_swf, offered_load, rescale_load
from scheduler.workloads import WORKLOADS, generate

st.set_page_config(page_title="Adaptive CPU Scheduler", layout="wide")
st.title("Adaptive CPU Scheduler: shadow-replay policy selection")
st.caption("Compare FCFS, SJF, Round Robin and the adaptive scheduler on your own workload. "
           "All times are in simulator ticks.")

# ----------------------------------------------------------------- sidebar
with st.sidebar:
    st.header("1. Workload")
    source = st.radio("Source", ["Generated", "Upload CSV", "Upload real trace (SWF)", "Example CSV"])
    jobs, label = None, ""
    try:
        if source == "Generated":
            wname = st.selectbox("Workload type", list(WORKLOADS), index=list(WORKLOADS).index("phased_mix"))
            seed = st.number_input("Random seed", 0, 10_000, 6)
            jobs, label = generate(wname, int(seed)), f"{wname} (seed {int(seed)})"
        elif source == "Upload CSV":
            f = st.file_uploader("CSV with columns: arrival, burst, [class], [pid]", type=["csv"])
            if f is not None:
                jobs, label = load_csv(io.BytesIO(f.getvalue())), f.name
        elif source == "Upload real trace (SWF)":
            f = st.file_uploader("Standard Workload Format file (.swf or .swf.gz)", type=["swf", "txt", "gz"])
            n = st.slider("Jobs to use", 50, 1000, 300, step=50)
            skip = st.number_input("Skip first N jobs", 0, 1_000_000, 0, step=100)
            if f is not None:
                jobs, label = load_swf(io.BytesIO(f.getvalue()), max_jobs=int(n), start=int(skip)), f.name
        else:
            jobs, label = load_csv("examples/sample_workload.csv"), "example CSV"
        if jobs and st.checkbox("Rescale arrival gaps to a target load", value=False):
            target = st.slider("Target load (1.0 = CPU always busy)", 0.3, 1.2, 0.9, 0.05)
            jobs = rescale_load(jobs, target)
    except WorkloadError as e:
        st.error(str(e))
        jobs = None

    st.header("2. System")
    quantum = st.slider("Round Robin quantum", 1, 10, 4)
    cs = st.slider("Context-switch cost (ticks)", 0, 5, 1)
    sp = st.slider("Rule-change penalty (ticks)", 0, 5, 1)

    st.header("3. Adaptive scheduler")
    mean_b = sum(j.burst for j in jobs) / len(jobs) if jobs else 10
    auto_interval = 10 if mean_b <= 40 else max(10, round(0.5 * mean_b))
    auto = st.checkbox(f"Auto check interval ({auto_interval} ticks for this workload)", value=True,
                       help="Real traces have very long jobs, so checking every 10 ticks would mean "
                            "tens of thousands of trial runs. Auto = 10 ticks for short jobs, "
                            "otherwise half the mean burst.")
    if auto:
        interval = auto_interval
    else:
        top = max(50, int(4 * mean_b))
        interval = st.slider("Check every N ticks", 5, top, min(auto_interval, top))
    window = st.slider("Trial-run window (recent jobs)", 4, 30, 12)
    margin = st.slider("Switch only if better by", 0.0, 0.30, 0.05, 0.01, format="%.2f")
    patience = st.slider("...on this many checks in a row", 1, 4, 2)
    initial = st.selectbox("Starting rule", ["SJF", "FCFS", f"RR{quantum}"])
    est_mode = st.selectbox("Burst estimate source", ["history", "last2", "tsafrir", "requested", "corrected"],
                            help="history = running average of past jobs of the same user/class. last2 = average of the "
                                 "user's last two finished jobs. tsafrir = the published predictor (last two jobs submitted "
                                 "earlier and finished; first job uses the request; never above the request). "
                                 "requested = the runtime "
                                 "the user asked for (SWF logs that include it). corrected = requested x the "
                                 "user's learned actual/requested ratio.")
    ref = st.checkbox("Show SJF* (cheating reference: knows true bursts)", value=True)

# ----------------------------------------------------------------- main panel
if jobs is None:
    st.info("Choose or upload a workload in the sidebar.")
    st.stop()

load = offered_load(jobs)
bursts = pd.Series([j.burst for j in jobs])
c1, c2, c3, c4 = st.columns(4)
c1.metric("Jobs", len(jobs))
c2.metric("Offered load", f"{load:.2f}")
c3.metric("Mean burst", f"{bursts.mean():.1f}")
c4.metric("Burst variability (CV)", f"{bursts.std(ddof=0) / bursts.mean():.2f}")
if load > 1.0:
    st.warning(f"Offered load is {load:.2f} (> 1): jobs arrive faster than the CPU can serve them, "
               "so waits grow throughout the run. Results are valid but extreme; consider rescaling.")
elif load < 0.4:
    st.warning(f"Offered load is only {load:.2f}: the CPU is mostly idle, so every rule looks the same.")

settings = Settings(quantum=quantum, cs_cost=cs, switch_penalty=sp, check_interval=interval,
                    window_jobs=window, margin=margin, patience=patience, initial=initial,
                    estimator=est_mode)
if est_mode != "history" and not any(j.req for j in jobs):
    st.info("This workload has no requested times (only some SWF logs include them), "
            "so the estimator falls back to history.")
with st.spinner("Running all methods (workloads with very long jobs can take a few seconds)..."):
    engines = compare(jobs, settings, include_cheating_reference=ref)

rows = []
for name, e in engines.items():
    m = e.metrics()
    rows.append({"method": name, "avg wait": m["avg_wait"], "p95 wait": m["p95_wait"],
                 "max wait": m["max_wait"], "avg response": m["avg_response"],
                 "avg turnaround": m["avg_turnaround"], "context switches": m["ctx_switches"],
                 "rule changes": m["policy_switches"]})
df = pd.DataFrame(rows).set_index("method")

st.subheader(f"Results on: {label}")
st.dataframe(df.round(2))
realistic = df.drop(index=[i for i in df.index if i.startswith("SJF*")], errors="ignore")
best = realistic["avg wait"].idxmin()
shadow = df.loc["Shadow (adaptive)", "avg wait"]
st.write(f"Best realistic method on average wait: **{best}** "
         f"(adaptive: {shadow:.2f}, best single fixed rule: "
         f"{realistic.loc[[i for i in realistic.index if i in ('FCFS', 'SJF', f'RR{quantum}')], 'avg wait'].min():.2f}). "
         "SJF* is only a reference: a real OS cannot know burst times in advance.")

left, right = st.columns(2)
with left:
    st.caption("Average wait (lower is better)")
    st.bar_chart(df["avg wait"])
with right:
    st.caption("95th-percentile wait (lower is better)")
    st.bar_chart(df["p95 wait"])

# which rule was active when
st.subheader("Which rule the adaptive scheduler used over time")
sh = engines["Shadow (adaptive)"]
segs = policy_segments(sh)
colors = {"FCFS": "#4C78A8", "SJF": "#54A24B", f"RR{quantum}": "#E45756"}
fig, ax = plt.subplots(figsize=(10, 1.6))
for a, b, p in segs:
    ax.barh(0, b - a, left=a, color=colors.get(p, "gray"), edgecolor="white")
ax.plot([j.arrival for j in jobs], [0.55] * len(jobs), "|", color="black", markersize=6)
ax.set_yticks([]); ax.set_xlabel("time (ticks)   |  black ticks = job arrivals")
ax.legend(handles=[plt.Rectangle((0, 0), 1, 1, color=c) for c in colors.values()],
          labels=list(colors), ncol=3, loc="upper center", bbox_to_anchor=(0.5, 1.5), frameon=False)
st.pyplot(fig)
if sh.switch_log:
    st.write("Rule changes: " + ", ".join(f"t={t}: {o}→{n}" for t, o, n in sh.switch_log))
else:
    st.write("The adaptive scheduler never changed rule on this workload "
             "(no trial run beat the starting rule by the required margin).")

with st.expander("Show the jobs"):
    st.dataframe(pd.DataFrame([{"pid": j.pid, "arrival": j.arrival, "burst": j.burst, "class": j.cls}
                               for j in jobs]))
st.caption("One run is one random sample. For conclusions use many seeds: "
           "`python -m experiments.run_experiments --runs 100`.")
