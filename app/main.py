"""
URL Shortener — Fully Instrumented for Observability

This app demonstrates THREE pillars of observability:
1. METRICS: Prometheus counters, histograms, gauges
2. LOGS:    Structured JSON logs with request context
3. TRACES:  OpenTelemetry distributed tracing (via headers)

Interview point:
"Show me a well-instrumented service."
This file is your answer.
"""

import time
import os
import json
import hashlib
import socket
import logging
import uuid
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.responses import RedirectResponse
from pydantic import BaseModel

import redis

# ── Prometheus client library ─────────────────────────────────
# prometheus_client gives us the metric types:
# Counter, Histogram, Gauge, Summary
from prometheus_client import (
    Counter,
    Histogram,
    Gauge,
    generate_latest,
    CONTENT_TYPE_LATEST,
    CollectorRegistry,
    REGISTRY,
)

# ─────────────────────────────────────────────────────────────
# STRUCTURED LOGGING SETUP
# ─────────────────────────────────────────────────────────────
# Why JSON logs?
# - Machine parseable by Loki, CloudWatch, Splunk
# - No regex needed to extract fields
# - Every field is queryable in Grafana
# - Consistent format across all services

class JSONFormatter(logging.Formatter):
    """
    Formats every log record as a JSON object.
    Each field becomes a queryable dimension in Loki.
    """
    def format(self, record):
        log_record = {
            # Standard fields present in every log line
            "timestamp": self.formatTime(record, "%Y-%m-%dT%H:%M:%S.%fZ"),
            "level":     record.levelname,
            "logger":    record.name,
            "message":   record.getMessage(),

            # Service identification
            # These let you filter logs by service in Grafana
            "service":   "url-shortener",
            "version":   os.getenv("APP_VERSION", "1.0.0"),

            # Kubernetes pod information
            # Injected as env vars by Kubernetes downward API
            # Lets you trace a log to its exact pod
            "pod":       os.getenv("POD_NAME", socket.gethostname()),
            "namespace": os.getenv("POD_NAMESPACE", "default"),
            "node":      os.getenv("NODE_NAME", "unknown"),
        }

        # Add any extra fields passed with the log call
        # e.g., logger.info("msg", extra={"request_id": "abc"})
        if hasattr(record, "request_id"):
            log_record["request_id"] = record.request_id
        if hasattr(record, "duration_ms"):
            log_record["duration_ms"] = record.duration_ms
        if hasattr(record, "status_code"):
            log_record["status_code"] = record.status_code
        if hasattr(record, "endpoint"):
            log_record["endpoint"] = record.endpoint
        if hasattr(record, "method"):
            log_record["method"] = record.method
        if hasattr(record, "event"):
            log_record["event"] = record.event

        # Include exception info if present
        if record.exc_info:
            log_record["exception"] = self.formatException(record.exc_info)

        return json.dumps(log_record)

# Configure the root logger with our JSON formatter
handler = logging.StreamHandler()
handler.setFormatter(JSONFormatter())

logger = logging.getLogger("url-shortener")
logger.addHandler(handler)
logger.setLevel(
    logging.DEBUG if os.getenv("LOG_LEVEL", "info").lower() == "debug"
    else logging.INFO
)

# ─────────────────────────────────────────────────────────────
# PROMETHEUS METRICS DEFINITION
# ─────────────────────────────────────────────────────────────
# Metrics are defined at module level (global variables).
# They persist across requests — that's how counters accumulate.
#
# Naming convention:
# <namespace>_<subsystem>_<name>_<unit>
# Example: http_requests_total, http_request_duration_seconds

# ── HTTP Request Counter ──────────────────────────────────────
# Counter: only goes up, never resets (until process restart).
# Use rate() in PromQL to get requests per second.
#
# Labels (dimensions):
# method:      GET, POST, DELETE
# endpoint:    /health, /shorten, /r/{code}
# status_code: 200, 404, 503
#
# Interview: "Why use labels instead of separate metrics?"
# Labels let you slice one metric by multiple dimensions.
# 1 metric with 3 labels = 1 × n × m × p time series
# vs creating separate metrics for every combination.
HTTP_REQUESTS_TOTAL = Counter(
    name="http_requests_total",
    documentation="Total number of HTTP requests received",
    labelnames=["method", "endpoint", "status_code"]
)

# ── HTTP Latency Histogram ────────────────────────────────────
# Histogram: records the distribution of values.
# Unlike average, histogram lets you calculate percentiles.
#
# Why p99 instead of average?
# Average: "on average, requests take 50ms"
# p99: "99% of requests complete in under 200ms"
#      "1% of requests (your worst users) take longer"
#
# Buckets define the histogram resolution.
# Each bucket counts requests that completed <= that duration.
# Prometheus uses these to calculate percentiles via PromQL.
HTTP_REQUEST_DURATION = Histogram(
    name="http_request_duration_seconds",
    documentation="HTTP request duration in seconds",
    labelnames=["method", "endpoint"],
    buckets=[
        0.005,  # 5ms
        0.01,   # 10ms
        0.025,  # 25ms
        0.05,   # 50ms
        0.1,    # 100ms
        0.25,   # 250ms
        0.5,    # 500ms
        1.0,    # 1s
        2.5,    # 2.5s
        5.0,    # 5s
        10.0,   # 10s
    ]
)

# ── Business Metrics ──────────────────────────────────────────
# Don't just measure infrastructure — measure business outcomes.
# "How many URLs shortened per minute?" is a business KPI.

URLS_SHORTENED_TOTAL = Counter(
    name="urls_shortened_total",
    documentation="Total number of URLs that have been shortened"
)

REDIRECTS_TOTAL = Counter(
    name="redirects_total",
    documentation="Total number of redirect requests served",
    labelnames=["short_code"]
)

# ── Redis Health Gauge ────────────────────────────────────────
# Gauge: can go up or down.
# Perfect for: current state, not cumulative events.
# 1 = connected, 0 = disconnected
# Alert: if this drops to 0 for > 1 minute
REDIS_CONNECTED = Gauge(
    name="redis_connected",
    documentation="Whether Redis is currently connected (1=yes, 0=no)"
)

# ── Redis Error Counter ───────────────────────────────────────
REDIS_ERRORS_TOTAL = Counter(
    name="redis_errors_total",
    documentation="Total Redis operation errors",
    labelnames=["operation"]
)

# ── Active Requests Gauge ─────────────────────────────────────
# How many requests are currently being processed?
# Useful for detecting request queuing / overload.
ACTIVE_REQUESTS = Gauge(
    name="http_active_requests",
    documentation="Number of HTTP requests currently being processed"
)

# ─────────────────────────────────────────────────────────────
# REDIS CONNECTION
# ─────────────────────────────────────────────────────────────
def get_redis():
    return redis.Redis(
        host=os.getenv("REDIS_HOST", "redis"),
        port=int(os.getenv("REDIS_PORT", 6379)),
        decode_responses=True,
        socket_connect_timeout=5,
        socket_timeout=5,
    )

r = get_redis()

# ─────────────────────────────────────────────────────────────
# FASTAPI APPLICATION
# ─────────────────────────────────────────────────────────────
app = FastAPI(
    title="URL Shortener — Observable Edition",
    description="Full observability: metrics, logs, traces",
    version="1.0.0"
)

# ─────────────────────────────────────────────────────────────
# METRICS MIDDLEWARE
# ─────────────────────────────────────────────────────────────
# Middleware runs for EVERY request before and after the handler.
# This is where we record metrics and logs for every request.
# Your handler code doesn't need to know about metrics.

@app.middleware("http")
async def observability_middleware(request: Request, call_next):
    """
    Middleware that adds observability to every request:
    1. Generates a unique request ID for correlation
    2. Records start time for latency measurement
    3. Increments active requests gauge
    4. Calls the actual handler
    5. Records metrics after response
    6. Logs structured request info
    """
    # Generate unique request ID.
    # This ID should be passed to all downstream services
    # so you can correlate logs across services for one request.
    request_id = str(uuid.uuid4())[:8]

    # Normalize the path for metrics.
    # /r/abc123, /r/def456 should be ONE metric series (/r/{code})
    # not thousands of different time series (one per code).
    path = request.url.path
    normalized_path = normalize_path(path)

    # Track active requests (increment before, decrement after)
    ACTIVE_REQUESTS.inc()

    start_time = time.time()
    status_code = 500  # default if handler crashes

    try:
        # Add request_id to request state so handlers can use it
        request.state.request_id = request_id

        # Call the actual route handler
        response = await call_next(request)
        status_code = response.status_code
        return response

    except Exception as exc:
        # Handler raised an exception
        status_code = 500
        logger.error(
            "Unhandled exception in request",
            extra={
                "request_id": request_id,
                "method": request.method,
                "endpoint": normalized_path,
                "error": str(exc),
            }
        )
        raise

    finally:
        # This runs whether handler succeeded or failed
        duration = time.time() - start_time

        # Record Prometheus metrics
        HTTP_REQUESTS_TOTAL.labels(
            method=request.method,
            endpoint=normalized_path,
            status_code=str(status_code)
        ).inc()

        HTTP_REQUEST_DURATION.labels(
            method=request.method,
            endpoint=normalized_path
        ).observe(duration)

        ACTIVE_REQUESTS.dec()

        # Structured log for every request
        log_level = logging.WARNING if status_code >= 400 else logging.INFO
        logger.log(
            log_level,
            f"{request.method} {path} {status_code}",
            extra={
                "request_id":  request_id,
                "method":      request.method,
                "endpoint":    normalized_path,
                "path":        path,
                "status_code": status_code,
                "duration_ms": round(duration * 1000, 2),
                "event":       "http_request",
            }
        )


def normalize_path(path: str) -> str:
    """
    Normalize URL paths to prevent high cardinality metrics.

    High cardinality problem:
    Without normalization, /r/abc123 and /r/xyz789 create
    TWO separate metric time series. With thousands of short codes,
    you'd have thousands of time series — killing Prometheus performance.

    With normalization:
    /r/abc123 → /r/{code}   (all redirects = ONE time series)
    /stats/abc123 → /stats/{code}
    """
    import re
    # Replace 6-character hex codes with {code} placeholder
    path = re.sub(r'/r/[a-f0-9]{6}', '/r/{code}', path)
    path = re.sub(r'/stats/[a-f0-9]{6}', '/stats/{code}', path)
    return path

# ─────────────────────────────────────────────────────────────
# DATA MODEL
# ─────────────────────────────────────────────────────────────
class URLRequest(BaseModel):
    url: str

# ─────────────────────────────────────────────────────────────
# ENDPOINTS
# ─────────────────────────────────────────────────────────────

@app.get("/metrics")
def metrics():
    """
    Prometheus scrape endpoint.
    Returns all metrics in Prometheus text format.

    Prometheus calls this every 15 seconds.
    NEVER put this behind authentication in a scrape setup
    (Prometheus needs to reach it).
    In production: use network policies to restrict access.
    """
    return Response(
        content=generate_latest(REGISTRY),
        media_type=CONTENT_TYPE_LATEST
    )

@app.get("/health")
def health():
    """
    Health endpoint for:
    - Kubernetes liveness probe
    - Load balancer health checks
    - Uptime monitoring

    Returns 200 when healthy, 503 when unhealthy.
    Prometheus can scrape this too for uptime tracking.
    """
    try:
        r.ping()
        REDIS_CONNECTED.set(1)
        logger.debug("Health check: OK", extra={"event": "health_check"})
        return {
            "status":  "healthy",
            "redis":   "connected",
            "pod":     os.getenv("POD_NAME", socket.gethostname()),
            "version": os.getenv("APP_VERSION", "1.0.0"),
        }
    except redis.RedisError as e:
        # Set gauge to 0 — triggers alert if sustained
        REDIS_CONNECTED.set(0)
        REDIS_ERRORS_TOTAL.labels(operation="ping").inc()

        logger.error(
            "Health check failed: Redis unavailable",
            extra={
                "event": "health_check_failed",
                "error": str(e),
            }
        )
        raise HTTPException(
            status_code=503,
            detail="Redis unavailable"
        )

@app.get("/ready")
def ready():
    """
    Readiness probe — separate from liveness.

    Liveness:  Is the process alive? (if not, restart it)
    Readiness: Is the process ready to serve traffic?
               (if not, remove from load balancer but don't restart)

    Interview: "What is the difference between liveness and readiness?"
    Liveness failure = kill and restart the pod
    Readiness failure = stop sending traffic, but pod stays running
    Use case: pod is starting up and not ready yet
    """
    try:
        r.ping()
        return {"status": "ready"}
    except redis.RedisError:
        raise HTTPException(
            status_code=503,
            detail="Not ready: Redis unavailable"
        )

@app.post("/shorten")
def shorten(req: URLRequest, request: Request):
    """Shorten a URL and store in Redis"""
    request_id = getattr(request.state, "request_id", "unknown")

    logger.info(
        "Shortening URL",
        extra={
            "event":      "url_shorten_request",
            "request_id": request_id,
            "url":        req.url[:100],  # truncate for log safety
        }
    )

    try:
        code = hashlib.md5(
            f"{req.url}{time.time()}".encode()
        ).hexdigest()[:6]

        r.hset(f"url:{code}", mapping={
            "url":        req.url,
            "clicks":     0,
            "created_at": time.strftime("%Y-%m-%dT%H:%M:%SZ"),
        })

        # Increment business metric
        URLS_SHORTENED_TOTAL.inc()

        logger.info(
            "URL shortened successfully",
            extra={
                "event":      "url_shortened",
                "request_id": request_id,
                "code":       code,
            }
        )

        return {
            "short_code": code,
            "short_url":  f"/r/{code}",
        }

    except redis.RedisError as e:
        REDIS_ERRORS_TOTAL.labels(operation="hset").inc()
        logger.error(
            "Failed to store URL",
            extra={
                "event":      "url_shorten_failed",
                "request_id": request_id,
                "error":      str(e),
            }
        )
        raise HTTPException(status_code=503, detail="Storage error")

@app.get("/r/{code}")
def redirect(code: str, request: Request):
    """Follow a short URL redirect"""
    request_id = getattr(request.state, "request_id", "unknown")

    try:
        data = r.hgetall(f"url:{code}")
        if not data:
            logger.warning(
                "Short code not found",
                extra={
                    "event":      "redirect_not_found",
                    "request_id": request_id,
                    "code":       code,
                }
            )
            raise HTTPException(status_code=404, detail="Not found")

        r.hincrby(f"url:{code}", "clicks", 1)
        REDIRECTS_TOTAL.labels(short_code=code).inc()

        logger.info(
            "Redirect served",
            extra={
                "event":      "redirect_served",
                "request_id": request_id,
                "code":       code,
                "target_url": data["url"][:100],
            }
        )

        return RedirectResponse(url=data["url"])

    except redis.RedisError as e:
        REDIS_ERRORS_TOTAL.labels(operation="hgetall").inc()
        raise HTTPException(status_code=503, detail="Storage error")

@app.get("/stats/{code}")
def stats(code: str):
    """Get click statistics for a short URL"""
    try:
        data = r.hgetall(f"url:{code}")
        if not data:
            raise HTTPException(status_code=404, detail="Not found")
        return {
            "short_code": code,
            "url":        data["url"],
            "clicks":     int(data.get("clicks", 0)),
            "created_at": data.get("created_at", "unknown"),
        }
    except redis.RedisError as e:
        REDIS_ERRORS_TOTAL.labels(operation="stats").inc()
        raise HTTPException(status_code=503, detail="Storage error")

@app.get("/")
def root():
    return {
        "service":  "URL Shortener",
        "version":  os.getenv("APP_VERSION", "1.0.0"),
        "pod":      os.getenv("POD_NAME", socket.gethostname()),
        "docs":     "/docs",
        "metrics":  "/metrics",
        "health":   "/health",
    }
