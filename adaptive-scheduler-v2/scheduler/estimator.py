"""Honest burst-time estimation (exponential averaging, as in OS textbooks).

new_guess = alpha * last_actual + (1 - alpha) * old_guess      (kept per job class)

It also tracks how wrong recent guesses were. That number is the
"reliability" signal used by the controller's guard (Idea B).
"""
from collections import deque


class BurstEstimator:
    def __init__(self, alpha=0.5, default=8.0, window=8, err_cap=2.0):
        self.alpha = alpha
        self.default = default
        self.err_cap = err_cap
        self.tau = {}
        self.errors = deque(maxlen=window)

    def predict(self, cls: str) -> float:
        return self.tau.get(cls, self.default)

    def update(self, cls: str, est_used: float, actual: int):
        self.errors.append(min(abs(est_used - actual) / actual, self.err_cap))
        old = self.tau.get(cls, self.default)
        self.tau[cls] = self.alpha * actual + (1 - self.alpha) * old

    # hooks used by the engine (so other estimators can look at the whole job)
    def estimate(self, job) -> float:
        return self.predict(job.cls)

    def observe(self, job):
        self.update(job.cls, job.est, job.burst)

    @property
    def recent_error(self) -> float:
        """Mean relative error of the last few guesses (0 = perfect, capped at err_cap)."""
        return sum(self.errors) / len(self.errors) if self.errors else 0.0


class RequestedTimeEstimator(BurstEstimator):
    """Uses the runtime the USER asked for when submitting the job (SWF field 9).
    It is known at arrival, so it is an honest estimate (real batch schedulers use it too).

    mode='requested': guess = the requested time, as is.
    mode='corrected': guess = requested time x a learned ratio (actual / requested),
                      kept per user and falling back to the all-users ratio.
                      Users usually over-ask, so the ratio is typically well below 1.
    Jobs without a requested time fall back to the per-class history guess."""

    def __init__(self, mode="requested", ratio_alpha=0.3, ratio_cap=2.0, **kw):
        super().__init__(**kw)
        if mode not in ("requested", "corrected"):
            raise ValueError("mode must be 'requested' or 'corrected'")
        self.mode = mode
        self.ratio_alpha = ratio_alpha
        self.ratio_cap = ratio_cap
        self.ratio = {}
        self.global_ratio = 1.0

    def estimate(self, job) -> float:
        if job.req is None:
            return self.predict(job.cls)
        if self.mode == "requested":
            return float(job.req)
        return max(1.0, job.req * self.ratio.get(job.cls, self.global_ratio))

    def observe(self, job):
        super().observe(job)
        if job.req:
            r = min(job.burst / job.req, self.ratio_cap)
            a = self.ratio_alpha
            self.ratio[job.cls] = a * r + (1 - a) * self.ratio.get(job.cls, self.global_ratio)
            self.global_ratio = a * r + (1 - a) * self.global_ratio


class Last2Estimator(BurstEstimator):
    """Tsafrir-style history predictor: the guess for a job is the average of the actual
    runtimes of the LAST TWO jobs of the same user/class (Tsafrir, Etsion & Feitelson, 2007).
    First job of a user: the requested time if the trace has one, else the default guess.
    NOTE: this is the simple predictor only; the original paper also adaptively corrects
    predictions that turn out too short, which is not replicated here."""

    def __init__(self, **kw):
        super().__init__(**kw)
        self.recent = {}

    def estimate(self, job) -> float:
        h = self.recent.get(job.cls)
        if h:
            return sum(h) / len(h)
        return float(job.req) if job.req else self.predict(job.cls)

    def observe(self, job):
        super().observe(job)
        self.recent.setdefault(job.cls, deque(maxlen=2)).append(job.burst)


class TsafrirEstimator(BurstEstimator):
    """The runtime predictor of Tsafrir, Etsion & Feitelson, "Backfilling Using System-Generated
    Predictions Rather Than User Runtime Estimates", IEEE TPDS 2007 (Section 3.1):

      1. The prediction for a new job is the AVERAGE runtime of the `window` (default 2) most recent
         jobs of the same user that were submitted before it AND have already terminated.
      2. If the user has no such jobs yet, fall back on the user's estimate (the requested time).
      3. If the prediction is larger than the job's own estimate, discard it and use the estimate
         (the job would be killed at its estimate anyway).

    What the paper adds that is NOT needed here: "prediction correction" (raising a prediction once
    a job outlives it) exists because backfilling computes reservations from predicted end times of
    RUNNING jobs. Our scheduler is single-CPU and non-preemptive and only uses a prediction to ORDER
    waiting jobs at the moment one is chosen, so correction would change nothing.
    window=1/2/3/... lets us test the paper's finding that a very short window works best.
    """

    def __init__(self, window=2, cap_at_request=True, use_request=True, **kw):
        super().__init__(**kw)
        if window < 1:
            raise ValueError("window must be at least 1")
        self.window = window
        self.cap = cap_at_request
        self.use_request = use_request           # False = ignore requested times completely (ablation)
        self.terminated = {}                     # class -> [(arrival, burst)] of finished jobs

    def estimate(self, job) -> float:
        hist = [h for h in self.terminated.get(job.cls, ()) if h[0] < job.arrival]
        hist.sort(key=lambda h: h[0], reverse=True)          # most recently SUBMITTED first
        recent = hist[:self.window]
        req = job.req if self.use_request else None
        if recent:
            pred = sum(b for _, b in recent) / len(recent)
        else:                                                # no history: the user's estimate
            pred = float(req) if req else self.predict(job.cls)
        if self.cap and req and pred > req:                  # an estimate is also the kill time
            pred = float(req)
        return pred

    def observe(self, job):
        super().observe(job)
        lst = self.terminated.setdefault(job.cls, [])
        lst.append((job.arrival, job.burst))
        if len(lst) > max(60, 5 * self.window):              # keep memory bounded
            del lst[0]
