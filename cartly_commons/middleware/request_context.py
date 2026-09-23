"""Request context propagation for ASGI services.

Every inbound HTTP request gets a RequestContext (request id, route, timings) that is available to
any code running in the request via `current_request_context()`. The context also keeps a replay
buffer of the response body so that error reports and late-arriving span enrichment can include
what the service actually returned.

Contexts are indexed by request id so the ErrorReporter can look them up after the response has
been sent; the reporter releases a context once it has been flushed.
"""
import contextvars
import time
import uuid
from dataclasses import dataclass, field
from typing import Dict, Optional

DEFAULT_REPLAY_BUFFER_BYTES = 512 * 1024

_current: contextvars.ContextVar[Optional["RequestContext"]] = contextvars.ContextVar("cartly_request_context", default=None)
_contexts: Dict[str, "RequestContext"] = {}


@dataclass
class RequestContext:
    request_id: str
    method: str
    path: str
    started_at: float = field(default_factory=time.time)
    status: Optional[int] = None
    error: Optional[str] = None
    replay: bytearray = field(default_factory=bytearray)
    replay_len: int = 0

    def record_body(self, chunk: bytes) -> None:
        end = min(self.replay_len + len(chunk), len(self.replay))
        self.replay[self.replay_len:end] = chunk[: end - self.replay_len]
        self.replay_len = end


def current_request_context() -> Optional[RequestContext]:
    return _current.get()


def get_context(request_id: str) -> Optional[RequestContext]:
    return _contexts.get(request_id)


def release_context(request_id: str) -> None:
    _contexts.pop(request_id, None)


class RequestContextMiddleware:
    def __init__(self, app, replay_buffer_bytes: int = DEFAULT_REPLAY_BUFFER_BYTES,
                 exclude_paths: tuple = ("/metrics", "/healthz", "/readyz")):
        self.app = app
        self.replay_buffer_bytes = replay_buffer_bytes
        self.exclude_paths = exclude_paths

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http" or scope.get("path") in self.exclude_paths:
            return await self.app(scope, receive, send)

        headers = dict(scope.get("headers") or [])
        request_id = headers.get(b"x-request-id", b"").decode() or uuid.uuid4().hex
        ctx = RequestContext(request_id=request_id, method=scope.get("method", ""), path=scope.get("path", ""),
                             replay=bytearray(b"\x00" * self.replay_buffer_bytes))
        _contexts[request_id] = ctx
        token = _current.set(ctx)

        async def send_with_context(message):
            if message["type"] == "http.response.start":
                ctx.status = message["status"]
                message.setdefault("headers", []).append((b"x-request-id", request_id.encode()))
            elif message["type"] == "http.response.body":
                ctx.record_body(message.get("body", b""))
            await send(message)

        try:
            await self.app(scope, receive, send_with_context)
        except Exception as exc:
            ctx.error = repr(exc)
            # Error reports are built synchronously from the context, so it can be released now.
            release_context(request_id)
            raise
        finally:
            _current.reset(token)
