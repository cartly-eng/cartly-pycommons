"""Single-line JSON logging with OpenTelemetry trace correlation."""
import json
import logging
import sys
import traceback

_EXTRA_KEYS = ("route", "status", "duration_ms", "order_id", "sku", "error", "attempt", "request_id")


class JsonFormatter(logging.Formatter):
    def __init__(self, service: str, version: str):
        super().__init__()
        self.service = service
        self.version = version

    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "ts": self.formatTime(record, "%Y-%m-%dT%H:%M:%S") + f".{int(record.msecs):03d}Z",
            "level": record.levelname.lower(),
            "service": self.service,
            "version": self.version,
            "msg": record.getMessage(),
        }
        try:
            from opentelemetry import trace
            ctx = trace.get_current_span().get_span_context()
            if ctx.is_valid:
                payload["trace_id"] = format(ctx.trace_id, "032x")
                payload["span_id"] = format(ctx.span_id, "016x")
        except ImportError:
            pass
        for key in _EXTRA_KEYS:
            if hasattr(record, key):
                payload[key] = getattr(record, key)
        if record.exc_info:
            payload["stacktrace"] = "".join(traceback.format_exception(*record.exc_info))
        return json.dumps(payload)


def configure(service: str, version: str, level: int = logging.INFO) -> logging.Logger:
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JsonFormatter(service, version))
    logging.root.handlers = [handler]
    logging.root.setLevel(level)
    for noisy in ("uvicorn.access", "httpx", "httpcore"):
        logging.getLogger(noisy).setLevel(logging.WARNING)
    return logging.getLogger(service)
