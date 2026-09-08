# Changelog

## 1.4.0
- New `cartly_commons.middleware.RequestContextMiddleware`: request id propagation (`x-request-id`),
  `current_request_context()`, and a response replay buffer for error reports / late span enrichment.

## 1.3.2
- logging: `request_id` is emitted as a structured field.
- http: timeouts are classified as `timeout`, not `error`.

## 1.3.0
- `cartly_commons.http.timed_call` for outbound call latency histograms.

## 1.2.0
- Structured JSON logging (`cartly_commons.logging`).
