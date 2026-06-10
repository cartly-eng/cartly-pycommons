"""Outbound HTTP helpers."""
import time
from contextlib import contextmanager


@contextmanager
def timed_call(histogram, service: str, target: str, timeout_exc: tuple = ()):
    """Observe an outbound call's duration on a prometheus Histogram labelled (service, target, outcome)."""
    start = time.perf_counter()
    outcome = "ok"
    try:
        yield
    except timeout_exc:
        outcome = "timeout"
        raise
    except Exception:
        outcome = "error"
        raise
    finally:
        histogram.labels(service, target, outcome).observe(time.perf_counter() - start)
