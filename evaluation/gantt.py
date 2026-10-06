import matplotlib
import matplotlib.pyplot as plt


def draw_gantt(ax, result, title=""):
    """Draw a Gantt chart from ScheduleResult.timeline on a matplotlib axis."""
    pids = sorted({pid for pid, _, _ in result.timeline})
    cmap = plt.get_cmap("tab20")
    for pid, start, end in result.timeline:
        ax.barh(pids.index(pid), end - start, left=start, color=cmap(pids.index(pid) % 20),
                edgecolor="black", linewidth=0.6)
    ax.set_yticks(range(len(pids)))
    ax.set_yticklabels([f"P{p}" for p in pids])
    ax.set_xlabel("Time"); ax.set_title(title, fontsize=10, fontweight="bold")
    ax.grid(axis="x", linestyle="--", alpha=0.5)
    ax.invert_yaxis()
