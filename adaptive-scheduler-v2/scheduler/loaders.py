"""Load your own workloads: a simple CSV, or a real trace in Standard Workload Format (SWF). A .gz file works as is (no need to unzip).

CSV columns (header row required):
    arrival   when the job shows up (>= 0)
    burst     how long it needs the CPU (> 0)
    class     OPTIONAL, which program/user it belongs to (the estimator learns per class)
    pid       OPTIONAL, job id (assigned automatically if missing)
Times may be decimals; they are rounded up to whole ticks (burst is at least 1).

SWF (https://www.cs.huji.ac.il/labs/parallel/workload/) is the standard format of the
Parallel Workloads Archive. Each line has 18 fields; we use submit time (field 2),
run time (field 4) and user id (field 12, used as the job class). Lines starting with ';'
are comments. NOTE: those jobs ran on many processors; here each is treated as one
burst on a single CPU. That is a simplification, so say so in your report.
"""
import csv
import gzip
import io
import math
import statistics

from .job import Job


class WorkloadError(ValueError):
    """Raised with a human-readable message when a file cannot be used."""


def _ticks(x, minimum):
    return max(minimum, int(math.ceil(float(x) - 1e-9)))


def load_csv(source):
    """source: a file path, or a text/bytes file-like object (e.g. a Streamlit upload)."""
    if isinstance(source, (str, bytes)) and not hasattr(source, "read"):
        with open(source, newline="", encoding="utf-8-sig") as f:
            text = f.read()
    else:
        raw = source.read()
        text = raw.decode("utf-8-sig") if isinstance(raw, bytes) else raw

    reader = csv.DictReader(io.StringIO(text))
    if not reader.fieldnames:
        raise WorkloadError("The file is empty.")
    cols = {c.strip().lower(): c for c in reader.fieldnames}
    for need in ("arrival", "burst"):
        if need not in cols:
            raise WorkloadError(f"Missing column '{need}'. Found: {list(cols)}. "
                                "Required columns: arrival, burst (optional: class, pid).")
    jobs = []
    for n, row in enumerate(reader, start=2):
        try:
            arrival = _ticks(row[cols["arrival"]], 0)
            burst = _ticks(row[cols["burst"]], 1)
        except (TypeError, ValueError):
            raise WorkloadError(f"Row {n}: arrival/burst must be numbers "
                                f"(got {row[cols['arrival']]!r}, {row[cols['burst']]!r}).")
        if float(row[cols["arrival"]]) < 0 or float(row[cols["burst"]]) <= 0:
            raise WorkloadError(f"Row {n}: arrival must be >= 0 and burst must be > 0.")
        cls = (row.get(cols["class"]) or "default").strip() if "class" in cols else "default"
        pid = int(float(row[cols["pid"]])) if "pid" in cols and row[cols["pid"]] else len(jobs) + 1
        jobs.append(Job(pid, arrival, burst, cls or "default"))
    if not jobs:
        raise WorkloadError("The file has a header but no jobs.")
    if len({j.pid for j in jobs}) != len(jobs):
        for i, j in enumerate(jobs, start=1):          # duplicate ids: renumber safely
            j.pid = i
    return jobs


def load_swf(source, max_jobs=300, start=0, ticks_per_second=None):
    """Read a Standard Workload Format trace.

    max_jobs / start : take a slice of the trace (the first `max_jobs` after skipping `start`)
    ticks_per_second : time scale. None = automatic: the median run time becomes ~8 ticks,
                       so the simulator works with small numbers.
    """
    if isinstance(source, (str, bytes)) and not hasattr(source, "read"):
        with open(source, "rb") as f:
            raw = f.read()
    else:
        raw = source.read()
    if isinstance(raw, bytes):
        if raw[:2] == b"\x1f\x8b":                  # .gz file: the archive ships logs gzipped
            raw = gzip.decompress(raw)
        text = raw.decode("utf-8", errors="ignore")
    else:
        text = raw

    rows = []
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith(";"):
            continue
        f = line.split()
        if len(f) < 12:
            continue
        try:
            submit, run, user = float(f[1]), float(f[3]), f[11]
            req = float(f[8]) if len(f) > 8 else -1.0
        except ValueError:
            continue
        if submit < 0 or run <= 0:                    # -1 means "unknown" in SWF
            continue
        rows.append((submit, run, f"user{user}", req if req > 0 else None))
    if not rows:
        raise WorkloadError("No usable jobs found. Is this a Standard Workload Format file "
                            "(18 space-separated fields, ';' comment lines)?")
    rows.sort(key=lambda r: r[0])
    rows = rows[start:start + max_jobs]
    if not rows:
        raise WorkloadError(f"'start' ({start}) is beyond the end of the trace.")

    if ticks_per_second is None:
        ticks_per_second = 8.0 / statistics.median(r[1] for r in rows)
    t0 = rows[0][0]
    return [Job(i + 1, _ticks((s - t0) * ticks_per_second, 0), _ticks(r * ticks_per_second, 1), u,
                req=None if q is None else max(1.0, q * ticks_per_second))
            for i, (s, r, u, q) in enumerate(rows)]


def offered_load(jobs):
    span = max(j.arrival for j in jobs) + 1
    return sum(j.burst for j in jobs) / span


def rescale_load(jobs, target):
    """Stretch/compress the gaps between arrivals so the offered load is ~`target`.
    (A standard trick: real traces are often far too idle or too overloaded to be interesting.)
    Burst times are untouched."""
    if target <= 0:
        raise WorkloadError("target load must be positive")
    factor = offered_load(jobs) / target
    return [Job(j.pid, int(round(j.arrival * factor)), j.burst, j.cls, req=j.req) for j in jobs]
