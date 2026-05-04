import json
import logging

from cartly_commons.logging import JsonFormatter


def test_json_line():
    rec = logging.LogRecord("x", logging.INFO, __file__, 1, "hello %s", ("world",), None)
    out = json.loads(JsonFormatter("svc", "1.0").format(rec))
    assert out["msg"] == "hello world" and out["service"] == "svc" and out["level"] == "info"
