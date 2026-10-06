import dataclasses
import pandas as pd
import streamlit as st
import matplotlib.pyplot as plt

from config import DEFAULT_CONFIG
from core.process import Process
from evaluation.runner import run_all
from evaluation.gantt import draw_gantt
from data.workloads import BENCHMARK_WORKLOADS, generate_random_workload, WORKLOAD_TYPES

st.set_page_config(page_title="Adaptive CPU Scheduler", page_icon="⚡", layout="wide")
st.title("⚡ Lightweight Workload-Signature-Based Adaptive CPU Scheduler")
st.caption("Workload → Signature → Classification → Policy Selection → Simulation → Metrics")
st.markdown("---")

# ---------------- Sidebar ----------------
sb = st.sidebar
sb.header("⚙️ Workload")
mode = sb.radio("Input mode", ["Benchmark scenario", "Random workload", "Custom table"])
if mode == "Benchmark scenario":
    name = sb.selectbox("Scenario", list(BENCHMARK_WORKLOADS))
    base = BENCHMARK_WORKLOADS[name]
elif mode == "Random workload":
    wtype = sb.selectbox("Workload type", WORKLOAD_TYPES)
    n = sb.slider("Number of processes", 3, 20, 8)
    seed = sb.number_input("Seed", 0, 9999, 1)
    base = generate_random_workload(n, wtype, int(seed))
else:
    base = [Process(1, 0, 5, 2), Process(2, 1, 3, 1), Process(3, 2, 8, 3), Process(4, 3, 4, 2)]

sb.header("🎯 Scheduler settings")
objective = sb.radio("Objective profile", ["balanced", "responsive"],
                     help="balanced: low waiting/turnaround. responsive: low response time (time-sharing).")
cs_cost = sb.slider("Context-switch cost (time units)", 0.0, 2.0, DEFAULT_CONFIG.context_switch_cost, 0.1)
rr_q = sb.slider("Baseline Round Robin quantum", 1, 10, DEFAULT_CONFIG.fixed_rr_quantum)
with sb.expander("Classifier thresholds"):
    cv_t = st.slider("High-variability CV", 0.2, 2.0, DEFAULT_CONFIG.high_variability_cv, 0.05)
    cpu_t = st.slider("CPU-intensive avg burst >", 4, 20, int(DEFAULT_CONFIG.cpu_intensive_avg_burst))
    short_t = st.slider("Short-burst limit", 1, 8, int(DEFAULT_CONFIG.short_burst_limit))
cfg = dataclasses.replace(DEFAULT_CONFIG, objective=objective, context_switch_cost=cs_cost,
                          fixed_rr_quantum=rr_q, high_variability_cv=cv_t,
                          cpu_intensive_avg_burst=cpu_t, short_burst_limit=short_t)

# ---------------- Process table ----------------
df_in = pd.DataFrame([{"PID": p.pid, "Arrival Time": p.arrival_time, "Burst Time": p.burst_time,
                       "Priority": p.priority} for p in base])
edited = st.data_editor(df_in, num_rows="dynamic", use_container_width=True, key=f"tbl_{mode}")

if st.button("🚀 Run simulation", type="primary", use_container_width=True):
    try:
        workload = [Process(int(r["PID"]), int(r["Arrival Time"]), int(r["Burst Time"]), int(r["Priority"]))
                    for _, r in edited.iterrows()]
    except Exception as e:
        st.error(f"Invalid process table: {e}"); st.stop()
    if not workload:
        st.warning("Add at least one process."); st.stop()
    if len({p.pid for p in workload}) != len(workload):
        st.error("PIDs must be unique."); st.stop()

    table, results, decision, sig = run_all(workload, cfg)

    st.markdown("### 🔍 Workload signature")
    cols = st.columns(6)
    cols[0].metric("Avg burst", f"{sig['avg_burst']:.2f}")
    cols[1].metric("Burst CV", f"{sig['burst_cv']:.2f}")
    cols[2].metric("Short-burst ratio", f"{sig['short_burst_ratio']:.0%}")
    cols[3].metric("Arrival density", f"{sig['arrival_density']:.2f}")
    cols[4].metric("Load factor", f"{sig['load_factor']:.1f}")
    cols[5].metric("Priority levels", sig["distinct_priorities"])

    st.success(f"**Class:** `{decision['label']}`  →  **Policy:** `{decision['policy']}`")
    st.info(f"**Why:** {decision['reason']}")

    st.markdown("### 📊 Performance matrix")
    nice = table.rename(columns={"avg_waiting_time": "Avg Wait", "avg_turnaround_time": "Avg Turnaround",
                                 "avg_response_time": "Avg Response", "max_waiting_time": "Max Wait",
                                 "throughput": "Throughput", "context_switches": "Ctx Switches",
                                 "starved_processes": "Starved"})
    st.dataframe(nice.round(2), use_container_width=True, hide_index=True)

    st.markdown("### 📈 Comparison")
    colors = ["#ff9999", "#66b3ff", "#99ff99", "#ffcc99", "#c9a0ff"]
    fig, axes = plt.subplots(1, 3, figsize=(16, 4.5))
    for ax, (col, ttl) in zip(axes, [("avg_waiting_time", "Average waiting time"),
                                     ("avg_response_time", "Average response time"),
                                     ("context_switches", "Context switches")]):
        ax.bar(range(len(table)), table[col], color=colors)
        ax.set_xticks(range(len(table)))
        ax.set_xticklabels([a.replace("Adaptive -> ", "Adaptive\n") for a in table["Algorithm"]], rotation=20, fontsize=8)
        ax.set_title(ttl, fontweight="bold"); ax.grid(axis="y", linestyle="--", alpha=.6)
    plt.tight_layout(); st.pyplot(fig)

    st.markdown("### 🧭 Gantt charts")
    fig2, axs = plt.subplots(len(results), 1, figsize=(12, 2.2 * len(results)), sharex=True)
    for ax, (alg, res) in zip(axs, results.items()):
        draw_gantt(ax, res, alg)
    plt.tight_layout(); st.pyplot(fig2)
