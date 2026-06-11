from __future__ import annotations

import time
from contextlib import ExitStack, contextmanager
from typing import Optional

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint

try:
    from prometheus_client import Counter, Histogram, generate_latest, CONTENT_TYPE_LATEST
    PROMETHEUS_AVAILABLE = True
except ImportError:  # pragma: no cover
    PROMETHEUS_AVAILABLE = False
    Counter = None
    Histogram = None
    generate_latest = None
    CONTENT_TYPE_LATEST = "text/plain; version=0.0.4; charset=utf-8"

try:
    from opentelemetry import trace
    from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
    from opentelemetry.sdk.resources import Resource
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import BatchSpanProcessor
    OPENTELEMETRY_AVAILABLE = True
except ImportError:  # pragma: no cover
    OPENTELEMETRY_AVAILABLE = False
    trace = None

from ai_tracing import initialize_tracing, tracing_context
from config import get_settings

settings = get_settings()

if PROMETHEUS_AVAILABLE:
    HTTP_REQUEST_COUNT = Counter(
        "callitaday_http_requests_total",
        "Total HTTP requests",
        ["method", "path", "status_code"],
    )
    HTTP_REQUEST_LATENCY = Histogram(
        "callitaday_http_request_latency_seconds",
        "HTTP request latency in seconds",
        ["method", "path"],
    )
    TOOL_INVOCATIONS = Counter(
        "callitaday_tool_invocations_total",
        "Tool invocation count",
        ["tool_name"],
    )
    LLM_CALLS = Counter(
        "callitaday_llm_calls_total",
        "LLM call count",
        ["purpose"],
    )
    ERROR_COUNT = Counter(
        "callitaday_errors_total",
        "Total errors captured",
        ["scope"],
    )
    VECTOR_SEARCH_LATENCY = Histogram(
        "callitaday_vector_search_latency_seconds",
        "Vector search latency",
        ["operation"],
    )
    DB_QUERY_LATENCY = Histogram(
        "callitaday_db_query_latency_seconds",
        "Database query latency",
        ["operation"],
    )


def init_observability() -> None:
    initialize_tracing()
    if settings.OTEL_ENABLED and OPENTELEMETRY_AVAILABLE:
        resource = Resource.create({"service.name": "callitaday-backend"})
        provider = TracerProvider(resource=resource)
        exporter = OTLPSpanExporter(endpoint=settings.OTEL_EXPORTER_OTLP_ENDPOINT, insecure=settings.OTEL_INSECURE)
        provider.add_span_processor(BatchSpanProcessor(exporter))
        trace.set_tracer_provider(provider)


def metrics_response() -> Response:
    if not PROMETHEUS_AVAILABLE or not settings.PROMETHEUS_ENABLED:
        return Response("Prometheus metrics disabled", status_code=503)
    payload = generate_latest()
    return Response(payload, media_type=CONTENT_TYPE_LATEST)


class PrometheusMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        request_start = time.perf_counter()
        response = await call_next(request)
        if PROMETHEUS_AVAILABLE and settings.PROMETHEUS_ENABLED:
            HTTP_REQUEST_COUNT.labels(
                method=request.method,
                path=request.url.path,
                status_code=response.status_code,
            ).inc()
            HTTP_REQUEST_LATENCY.labels(method=request.method, path=request.url.path).observe(
                time.perf_counter() - request_start
            )
        return response


def record_tool_invocation(tool_name: str) -> None:
    if PROMETHEUS_AVAILABLE and settings.PROMETHEUS_ENABLED:
        TOOL_INVOCATIONS.labels(tool_name=tool_name).inc()


def record_llm_call(purpose: str) -> None:
    if PROMETHEUS_AVAILABLE and settings.PROMETHEUS_ENABLED:
        LLM_CALLS.labels(purpose=purpose).inc()


def record_error(scope: str) -> None:
    if PROMETHEUS_AVAILABLE and settings.PROMETHEUS_ENABLED:
        ERROR_COUNT.labels(scope=scope).inc()


@contextmanager
def trace_span(name: str, *, as_type: str = "span"):
    with ExitStack() as stack:
        if settings.OTEL_ENABLED and OPENTELEMETRY_AVAILABLE:
            tracer = trace.get_tracer(__name__)
            stack.enter_context(tracer.start_as_current_span(name))
        stack.enter_context(tracing_context(name=name, as_type=as_type))
        yield
