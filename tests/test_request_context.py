import asyncio

from cartly_commons.middleware.request_context import RequestContextMiddleware, get_context


async def _app(scope, receive, send):
    await send({"type": "http.response.start", "status": 200, "headers": []})
    await send({"type": "http.response.body", "body": b"hello"})


def test_context_records_status_and_body():
    sent = []

    async def send(msg):
        sent.append(msg)

    mw = RequestContextMiddleware(_app, replay_buffer_bytes=16)
    scope = {"type": "http", "method": "GET", "path": "/x", "headers": [(b"x-request-id", b"abc")]}
    asyncio.run(mw(scope, None, send))
    ctx = get_context("abc")
    assert ctx.status == 200
    assert bytes(ctx.replay[: ctx.replay_len]) == b"hello"
    assert (b"x-request-id", b"abc") in sent[0]["headers"]
