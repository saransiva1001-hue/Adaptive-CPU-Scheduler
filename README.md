# Lightweight Workload-Signature-Based Adaptive CPU Scheduler

    pip install streamlit pandas matplotlib
    python -m tests.test_schedulers     # 9 textbook-correctness tests
    python main.py                      # CLI demo on benchmark scenarios
    python experiments.py               # full evaluation -> results/{balanced,responsive}/
    streamlit run app.py                # interactive dashboard

Pipeline: Workload -> signature (core/signature.py) -> classify (core/adaptive.py)
-> select policy -> simulate (core/schedulers.py) -> metrics (evaluation/metrics.py).
All thresholds live in config.py.
