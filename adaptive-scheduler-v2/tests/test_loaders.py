"""Tests for CSV/SWF loading and the compare helper.  Run:  python -m tests.test_loaders"""
import io

from scheduler.compare import Settings, compare, policy_segments
from scheduler.loaders import WorkloadError, load_csv, load_swf, offered_load, rescale_load


def raises(fn, *a, **k):
    try:
        fn(*a, **k)
    except WorkloadError as e:
        return str(e)
    raise AssertionError("expected WorkloadError")


def test_csv_basic_and_optional_columns():
    jobs = load_csv(io.StringIO("arrival,burst\n0,5\n2,3\n"))
    assert [(j.arrival, j.burst, j.cls, j.pid) for j in jobs] == [(0, 5, "default", 1), (2, 3, "default", 2)]
    jobs = load_csv(io.StringIO("Arrival, Burst ,Class,PID\n0,5,a,10\n1,2,b,11\n".replace(" Burst ", "Burst")))
    assert [(j.cls, j.pid) for j in jobs] == [("a", 10), ("b", 11)]


def test_csv_decimals_round_up_and_burst_at_least_one():
    jobs = load_csv(io.StringIO("arrival,burst\n0.2,2.1\n1,0.3\n"))
    assert (jobs[0].arrival, jobs[0].burst) == (1, 3) and jobs[1].burst == 1


def test_csv_bytes_input_like_a_streamlit_upload():
    jobs = load_csv(io.BytesIO(b"\xef\xbb\xbfarrival,burst\n0,4\n"))
    assert len(jobs) == 1


def test_csv_clear_errors():
    assert "Missing column 'burst'" in raises(load_csv, io.StringIO("arrival,length\n0,5\n"))
    assert "Row 2" in raises(load_csv, io.StringIO("arrival,burst\nabc,5\n"))
    assert "burst must be > 0" in raises(load_csv, io.StringIO("arrival,burst\n0,0\n"))
    assert "no jobs" in raises(load_csv, io.StringIO("arrival,burst\n"))


def test_csv_duplicate_pids_are_renumbered():
    jobs = load_csv(io.StringIO("arrival,burst,pid\n0,5,1\n1,5,1\n"))
    assert sorted(j.pid for j in jobs) == [1, 2]


SWF = """; comment
1 0 0 3600 8 -1 -1 8 4000 -1 1 7 1 1 1 1 -1 -1
2 30 0 120 1 -1 -1 1 300 -1 1 3 1 1 1 1 -1 -1
3 60 0 -1 1 -1 -1 1 300 -1 5 4 1 1 1 1 -1 -1
4 90 0 240 1 -1 -1 1 300 -1 1 3 1 1 1 1 -1 -1
"""


def test_swf_skips_unknown_runtime_and_uses_user_as_class():
    jobs = load_swf(io.StringIO(SWF))
    assert len(jobs) == 3 and [j.cls for j in jobs] == ["user7", "user3", "user3"]
    assert jobs[0].arrival == 0 and all(j.burst >= 1 for j in jobs)


def test_swf_explicit_scale_slice_and_errors():
    jobs = load_swf(io.StringIO(SWF), ticks_per_second=0.1)
    assert jobs[0].burst == 360 and jobs[1].arrival == 3 and jobs[1].burst == 12
    assert len(load_swf(io.StringIO(SWF), max_jobs=2)) == 2
    assert "No usable jobs" in raises(load_swf, io.StringIO("; only comments\n"))
    assert "beyond the end" in raises(load_swf, io.StringIO(SWF), start=99)


def test_swf_gzip_is_read_directly():
    import gzip
    jobs = load_swf(io.BytesIO(gzip.compress(SWF.encode())))
    assert len(jobs) == 3 and jobs[0].cls == "user7"


def test_rescale_load_hits_target_roughly_and_keeps_bursts():
    jobs = load_csv(io.StringIO("arrival,burst\n" + "\n".join(f"{i * 2},{4}" for i in range(50))))
    out = rescale_load(jobs, 0.5)
    assert [j.burst for j in out] == [j.burst for j in jobs]
    assert abs(offered_load(out) - 0.5) < 0.05


def test_compare_runs_all_methods_and_segments_cover_the_run():
    jobs = load_csv("examples/sample_workload.csv")
    engines = compare(jobs, Settings())
    assert {"FCFS", "SJF", "RR4", "Shadow (adaptive)", "SJF* (cheats: true bursts)"} <= set(engines)
    for e in engines.values():
        assert len(e.done) == len(jobs)
    segs = policy_segments(engines["Shadow (adaptive)"])
    assert segs[0][0] == 0 and all(a[1] == b[0] for a, b in zip(segs, segs[1:]))
    assert segs[-1][1] == max(j.finish for j in engines["Shadow (adaptive)"].done)


if __name__ == "__main__":
    tests = [(k, v) for k, v in sorted(globals().items()) if k.startswith("test_")]
    for name, fn in tests:
        fn()
        print("PASS ", name)
    print(f"\nAll {len(tests)} tests passed.")
