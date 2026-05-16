# 📊 Full Observability Stack

> **Complete from scratch.** 
> Build a production-grade observability platform with Prometheus, Grafana, Loki, and Jaeger — monitoring a fully instrumented FastAPI URL Shortener.

---

## 📋 Table of Contents

- [What You Will Build](#what-you-will-build)
- [Architecture Overview](#architecture-overview)
- [The Three Pillars of Observability](#the-three-pillars-of-observability)
- [Prerequisites](#prerequisites)
- [Project Structure](#project-structure)
- [Step-by-Step Setup](#step-by-step-setup)
  - [Step 1 — Start Minikube](#step-1--start-minikube)
  - [Step 2 — Project Structure](#step-2--project-structure)
  - [Step 3 — The Application](#step-3--the-application)
  - [Step 4 — Requirements](#step-4--requirements)
  - [Step 5 — Dockerfile](#step-5--dockerfile)
  - [Step 6 — Build Docker Image](#step-6--build-docker-image)
  - [Step 7 — Kubernetes Namespace and RBAC](#step-7--kubernetes-namespace-and-rbac)
  - [Step 8 — Deploy Redis](#step-8--deploy-redis)
  - [Step 9 — Deploy the Application](#step-9--deploy-the-application)
  - [Step 10 — Verify Metrics Endpoint](#step-10--verify-metrics-endpoint)
  - [Step 11 — Install Prometheus Stack](#step-11--install-prometheus-stack)
  - [Step 12 — Create Custom Alert Rules](#step-12--create-custom-alert-rules)
  - [Step 13 — Install Loki (Log Aggregation)](#step-13--install-loki-log-aggregation)
  - [Step 14 — Install Jaeger (Distributed Tracing)](#step-14--install-jaeger-distributed-tracing)
  - [Step 15 — Grafana Dashboard as Code](#step-15--grafana-dashboard-as-code)
  - [Step 16 — Configure Alertmanager](#step-16--configure-alertmanager)
  - [Step 17 — Access Dashboards](#step-17--access-dashboards)
  - [Step 18 — Generate Traffic](#step-18--generate-traffic)
  - [Step 19 — PromQL Queries to Try](#step-19--promql-queries-to-try)
  - [Step 20 — Loki Log Queries](#step-20--loki-log-queries)
  - [Step 21 — Final Verification](#step-21--final-verification)
- [Key Concepts Explained](#key-concepts-explained)
- [Troubleshooting](#troubleshooting)
- [Interview Q&A](#interview-qa)

---

## What You Will Build

A **production-grade URL Shortener** service that is fully observable — every request generates metrics, logs, and traces automatically, with no manual instrumentation required in individual handlers.

**The Observability Stack:**

| Component | Role | Port |
|-----------|------|------|
| **Prometheus** | Scrapes and stores time-series metrics | 30090 |
| **Grafana** | Visualizes metrics, logs, and traces | 30030 |
| **Loki** | Aggregates and stores logs | internal |
| **Promtail** | Collects logs from pods, ships to Loki | DaemonSet |
| **Jaeger** | Stores and visualizes distributed traces | 30686 |
| **Alertmanager** | Routes alerts to Slack/email/PagerDuty | 30093 |

**The Application:**

| Component | Role | Port |
|-----------|------|------|
| **FastAPI URL Shortener** | Business logic + full instrumentation | 30080 |
| **Redis** | Persistent storage for short URLs | internal |

---

## Architecture Overview

```
┌──────────────────────────────────────────────────────────────┐
│                    Minikube Cluster                           │
│                                                              │
│  ┌─────────────────────────────────────────────────────┐    │
│  │  url-shortener namespace                             │    │
│  │                                                      │    │
│  │  ┌──────────────────┐    ┌──────────────────┐       │    │
│  │  │  FastAPI App     │    │  Redis           │       │    │
│  │  │  :8000           │───►│  :6379           │       │    │
│  │  │  /metrics ───────┼────┼──────────────────┼──┐    │    │
│  │  │  /health         │    │                  │  │    │    │
│  │  └──────────────────┘    └──────────────────┘  │    │    │
│  └──────────────────────────────────────────────│──┘    │    │
│                                                  │        │    │
│  ┌───────────────────────────────────────────────▼──┐    │    │
│  │  monitoring namespace                            │    │    │
│  │                                                  │    │    │
│  │  ┌────────────┐  ┌──────────┐  ┌─────────────┐  │    │    │
│  │  │ Prometheus │  │ Grafana  │  │    Loki     │  │    │    │
│  │  │ (scrapes)  │  │ (UI)     │  │  (logs)     │  │    │    │
│  │  └────────────┘  └──────────┘  └─────────────┘  │    │    │
│  │  ┌────────────┐  ┌──────────┐  ┌─────────────┐  │    │    │
│  │  │ Alertmgr   │  │  Jaeger  │  │  Promtail   │  │    │    │
│  │  │ (alerts)   │  │ (traces) │  │  (DaemonSet)│  │    │    │
│  │  └────────────┘  └──────────┘  └─────────────┘  │    │    │
│  └──────────────────────────────────────────────────┘    │    │
└──────────────────────────────────────────────────────────────┘
```

---

## The Three Pillars of Observability

| Pillar | Tool | Answers |
|--------|------|---------|
| **Metrics** | Prometheus + Grafana | *WHAT* is happening and *HOW MUCH* |
| **Logs** | Loki + Promtail | *WHAT* happened in detail |
| **Traces** | Jaeger | *WHY* is it slow / *WHERE* did it fail |

**The Four Golden Signals** (what every dashboard shows):

```
1. Traffic    → requests per second
2. Errors     → % of requests failing (5xx)
3. Latency    → p50, p95, p99 response times
4. Saturation → CPU %, memory %, queue depth
```

---

## Prerequisites

### Required Tools

| Tool | Minimum Version | Check Command |
|------|----------------|---------------|
| Docker | 20.x+ | `docker --version` |
| Minikube | 1.30+ | `minikube version` |
| kubectl | 1.27+ | `kubectl version --client` |
| Helm | 3.12+ | `helm version` |
| Python 3 | 3.8+ | `python3 --version` |
| curl | any | `curl --version` |

### Install Missing Tools

```bash
# Docker
curl -fsSL https://get.docker.com | sh
sudo usermod -aG docker $USER
newgrp docker

# Minikube
curl -LO https://storage.googleapis.com/minikube/releases/latest/minikube-linux-amd64
sudo install minikube-linux-amd64 /usr/local/bin/minikube

# kubectl
curl -LO "https://dl.k8s.io/release/$(curl -L -s https://dl.k8s.io/release/stable.txt)/bin/linux/amd64/kubectl"
chmod +x kubectl && sudo mv kubectl /usr/local/bin/

# Helm
curl https://raw.githubusercontent.com/helm/helm/main/scripts/get-helm-3 | bash
```

### Verify All Tools

```bash
echo "=== Prerequisites Check ==="
for tool in docker minikube kubectl helm python3 curl; do
  if command -v $tool &>/dev/null; then
    echo "✅ $tool: $($tool --version 2>&1 | head -1)"
  else
    echo "❌ $tool: NOT FOUND"
  fi
done
```

---

## Project Structure

```
day38-observability/
├── app/
│   ├── main.py                          # FastAPI app with full instrumentation
│   └── requirements.txt                 # Python dependencies
├── Dockerfile                           # Multi-stage production build
├── kubernetes/
│   ├── namespace.yaml                   # Namespace definitions
│   ├── redis.yaml                       # Redis deployment + service
│   └── app.yaml                         # App deployment + services
├── monitoring/
│   ├── prometheus/
│   │   ├── values.yaml                  # kube-prometheus-stack Helm values
│   │   └── alert-rules.yaml             # Custom PrometheusRule CRD
│   ├── grafana/
│   │   └── dashboards/
│   │       ├── url-shortener.json       # Dashboard JSON definition
│   │       └── configmap.yaml           # ConfigMap wrapping the dashboard
│   ├── loki/
│   │   └── values-fixed.yaml            # Loki + Promtail Helm values
│   └── alertmanager/
│       └── config.yaml                  # Alertmanager routing configuration
└── scripts/
    └── generate-traffic.sh              # Load generation script
```

---

## Step-by-Step Setup

### Step 1 — Start Minikube

Observability stack is memory-intensive. We need at least 6GB.

```bash
minikube start \
  --driver=docker \
  --memory=6144 \
  --cpus=4 \
  --kubernetes-version=v1.29.0

# Verify cluster is healthy
kubectl cluster-info
kubectl get nodes

# Enable metrics server (required for kubectl top commands)
minikube addons enable metrics-server

echo "✅ Minikube ready"
```

> **Why 6GB?**
> Prometheus: ~512MB | Grafana: ~256MB | Loki: ~512MB | Jaeger: ~512MB | App: ~256MB | System: ~1GB

---

### Step 2 — Project Structure

```bash
mkdir -p ~/projects/day38-observability
cd ~/projects/day38-observability

mkdir -p \
  app \
  kubernetes \
  monitoring/prometheus \
  monitoring/grafana/dashboards \
  monitoring/loki \
  monitoring/alertmanager \
  scripts

echo "✅ Directory structure created"
```

---

### Step 3 — The Application

Create the FastAPI application with **full observability instrumentation**:

```bash
cat > app/main.py << 'EOF'
"""
URL Shortener — Fully Instrumented for Observability

Three pillars of observability:
1. METRICS: Prometheus counters, histograms, gauges
2. LOGS:    Structured JSON logs with request context
3. TRACES:  Distributed tracing (via Jaeger)
"""

import time, os, json, hashlib, socket, logging, uuid
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.responses import RedirectResponse
from pydantic import BaseModel
from typing import Optional
import redis
from prometheus_client import (
    Counter, Histogram, Gauge,
    generate_latest, CONTENT_TYPE_LATEST, REGISTRY
)

# ── Structured JSON Logging ───────────────────────────────────
# JSON format: every field is queryable in Loki without regex
class JSONFormatter(logging.Formatter):
    def format(self, record):
        log_record = {
            "timestamp":  self.formatTime(record, "%Y-%m-%dT%H:%M:%S.%fZ"),
            "level":      record.levelname,
            "message":    record.getMessage(),
            "service":    "url-shortener",
            "version":    os.getenv("APP_VERSION", "1.0.0"),
            "pod":        os.getenv("POD_NAME", socket.gethostname()),
            "namespace":  os.getenv("POD_NAMESPACE", "default"),
            "node":       os.getenv("NODE_NAME", "unknown"),
        }
        for key, value in record.__dict__.items():
            if key not in ("msg","args","levelname","levelno","pathname",
                "filename","module","funcName","created","msecs",
                "relativeCreated","thread","threadName","processName",
                "process","name","exc_info","exc_text","stack_info","message"):
                if not key.startswith("_"):
                    log_record[key] = value
        if record.exc_info:
            log_record["exception"] = self.formatException(record.exc_info)
        return json.dumps(log_record)

handler = logging.StreamHandler()
handler.setFormatter(JSONFormatter())
logger = logging.getLogger("url-shortener")
logger.addHandler(handler)
logger.setLevel(logging.INFO)

# ── Prometheus Metrics ────────────────────────────────────────
# Golden Signal 1 & 2: Traffic and Errors
HTTP_REQUESTS_TOTAL = Counter(
    "http_requests_total",
    "Total HTTP requests",
    ["method", "endpoint", "status_code"]
)

# Golden Signal 3: Latency (Histogram enables percentiles)
HTTP_REQUEST_DURATION = Histogram(
    "http_request_duration_seconds",
    "HTTP request latency",
    ["method", "endpoint"],
    buckets=[0.005,0.01,0.025,0.05,0.1,0.25,0.5,1.0,2.5,5.0,10.0]
)

# Golden Signal 4: Saturation
ACTIVE_REQUESTS = Gauge("http_active_requests", "In-flight requests")

# Business metrics — tells you if the system is WORKING
URLS_SHORTENED = Counter("urls_shortened_total", "Total URLs shortened")
REDIRECTS_SERVED = Counter("redirects_served_total", "Total redirects", ["short_code"])

# Infrastructure health
REDIS_CONNECTED = Gauge("redis_connected", "Redis status: 1=up, 0=down")
REDIS_ERRORS = Counter("redis_errors_total", "Redis errors", ["operation"])

# ── Redis Connection ──────────────────────────────────────────
r = redis.Redis(
    host=os.getenv("REDIS_HOST", "redis"),
    port=int(os.getenv("REDIS_PORT", 6379)),
    decode_responses=True,
    socket_connect_timeout=5,
    socket_timeout=5,
)

app = FastAPI(title="URL Shortener — Observable Edition", version="1.0.0")

# ── Middleware: Instruments EVERY request ─────────────────────
# You add this once and ALL endpoints get metrics + logs
@app.middleware("http")
async def observability_middleware(request: Request, call_next):
    request_id = str(uuid.uuid4())[:8]
    start_time = time.time()
    status_code = 500

    import re
    path = request.url.path
    # Normalize path to prevent high-cardinality metrics
    # /r/abc123, /r/def456 → /r/{code}  (ONE time series)
    norm_path = re.sub(r'/r/[a-f0-9]{6}$', '/r/{code}', path)
    norm_path = re.sub(r'/stats/[a-f0-9]{6}$', '/stats/{code}', norm_path)

    ACTIVE_REQUESTS.inc()
    try:
        request.state.request_id = request_id
        response = await call_next(request)
        status_code = response.status_code
        return response
    except Exception as exc:
        logger.error("Unhandled exception", extra={
            "request_id": request_id, "error": str(exc), "path": path
        }, exc_info=True)
        raise
    finally:
        duration = time.time() - start_time
        HTTP_REQUESTS_TOTAL.labels(
            method=request.method,
            endpoint=norm_path,
            status_code=str(status_code)
        ).inc()
        HTTP_REQUEST_DURATION.labels(
            method=request.method,
            endpoint=norm_path
        ).observe(duration)
        ACTIVE_REQUESTS.dec()
        log_fn = logger.warning if status_code >= 400 else logger.info
        log_fn(f"{request.method} {path} {status_code}", extra={
            "event": "http_request",
            "request_id": request_id,
            "method": request.method,
            "endpoint": norm_path,
            "path": path,
            "status_code": status_code,
            "duration_ms": round(duration * 1000, 2),
        })

class URLRequest(BaseModel):
    url: str

@app.get("/metrics")
def metrics():
    """Prometheus scrape endpoint — called every 15s"""
    return Response(content=generate_latest(REGISTRY), media_type=CONTENT_TYPE_LATEST)

@app.get("/health")
def health():
    """Liveness probe — Kubernetes restarts pod if this fails"""
    try:
        r.ping()
        REDIS_CONNECTED.set(1)
        return {"status": "healthy", "redis": "connected",
                "pod": os.getenv("POD_NAME", socket.gethostname()),
                "version": os.getenv("APP_VERSION", "1.0.0")}
    except redis.RedisError as e:
        REDIS_CONNECTED.set(0)
        REDIS_ERRORS.labels(operation="ping").inc()
        logger.error("Health check failed", extra={"event": "redis_down", "error": str(e)})
        raise HTTPException(status_code=503, detail="Redis unavailable")

@app.get("/ready")
def ready():
    """Readiness probe — removes from load balancer if fails (no restart)"""
    try:
        r.ping()
        return {"status": "ready"}
    except redis.RedisError:
        raise HTTPException(status_code=503, detail="Not ready")

@app.post("/shorten")
def shorten(req: URLRequest, request: Request):
    request_id = getattr(request.state, "request_id", "unknown")
    logger.info("Shortening URL", extra={"event": "url_shorten_request",
        "request_id": request_id, "url": req.url[:100]})
    try:
        code = hashlib.md5(f"{req.url}{time.time()}".encode()).hexdigest()[:6]
        r.hset(f"url:{code}", mapping={
            "url": req.url, "clicks": 0,
            "created_at": time.strftime("%Y-%m-%dT%H:%M:%SZ")
        })
        URLS_SHORTENED.inc()
        logger.info("URL shortened", extra={"event": "url_shortened",
            "request_id": request_id, "code": code})
        return {"short_code": code, "short_url": f"/r/{code}"}
    except redis.RedisError as e:
        REDIS_ERRORS.labels(operation="hset").inc()
        raise HTTPException(status_code=503, detail="Storage error")

@app.get("/r/{code}")
def redirect_url(code: str, request: Request):
    request_id = getattr(request.state, "request_id", "unknown")
    try:
        data = r.hgetall(f"url:{code}")
        if not data:
            raise HTTPException(status_code=404, detail="Not found")
        r.hincrby(f"url:{code}", "clicks", 1)
        REDIRECTS_SERVED.labels(short_code=code).inc()
        logger.info("Redirect served", extra={"event": "redirect_served",
            "request_id": request_id, "code": code})
        return RedirectResponse(url=data["url"])
    except redis.RedisError:
        REDIS_ERRORS.labels(operation="hgetall").inc()
        raise HTTPException(status_code=503, detail="Storage error")

@app.get("/stats/{code}")
def stats(code: str):
    try:
        data = r.hgetall(f"url:{code}")
        if not data:
            raise HTTPException(status_code=404, detail="Not found")
        return {"short_code": code, "url": data["url"],
                "clicks": int(data.get("clicks", 0)),
                "created_at": data.get("created_at", "unknown")}
    except redis.RedisError:
        raise HTTPException(status_code=503, detail="Storage error")

@app.get("/")
def root():
    return {"service": "URL Shortener", "version": os.getenv("APP_VERSION", "1.0.0"),
            "docs": "/docs", "metrics": "/metrics", "health": "/health"}
EOF

echo "✅ Application created"
```

---

### Step 4 — Requirements

```bash
cat > app/requirements.txt << 'EOF'
fastapi==0.110.0
uvicorn==0.29.0
redis==5.0.3
pydantic==2.6.4
prometheus-client==0.20.0
EOF
```

---

### Step 5 — Dockerfile

```bash
cat > Dockerfile << 'EOF'
# Stage 1: Builder — installs dependencies (DISCARDED, never ships)
FROM python:3.11-slim AS builder
WORKDIR /app
COPY app/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Stage 2: Production — minimal image, runs the app
FROM python:3.11-slim AS production
WORKDIR /app

# Non-root user — security requirement
RUN addgroup --system appgroup && \
    adduser --system --ingroup appgroup appuser

# Copy only what's needed from builder
COPY --from=builder /usr/local/lib/python3.11/site-packages \
  /usr/local/lib/python3.11/site-packages
COPY --from=builder /usr/local/bin/uvicorn /usr/local/bin/uvicorn

COPY app/main.py .

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV APP_VERSION=1.0.0

USER appuser
EXPOSE 8000
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
EOF

cat > .dockerignore << 'EOF'
.git
.github
kubernetes/
monitoring/
scripts/
*.md
.env
**/__pycache__
**/*.pyc
EOF

echo "✅ Dockerfile created"
```

---

### Step 6 — Build Docker Image

> **Critical:** Build inside minikube's Docker daemon, not your host Docker. Otherwise Kubernetes cannot find the image.

```bash
cd ~/projects/day38-observability

# Switch to minikube's Docker daemon
eval $(minikube docker-env)

# Verify you're talking to minikube
docker info | grep "Name:"
# Should show: Name: minikube

# Build the image
docker build -t url-shortener:observable .

# Verify image exists
docker images | grep url-shortener

echo "✅ Image built inside minikube"
```

---

### Step 7 — Kubernetes Namespace and RBAC

```bash
cat > kubernetes/namespace.yaml << 'EOF'
apiVersion: v1
kind: Namespace
metadata:
  name: url-shortener
  labels:
    name: url-shortener
    monitoring: enabled
---
apiVersion: v1
kind: Namespace
metadata:
  name: monitoring
  labels:
    name: monitoring
EOF

kubectl apply -f kubernetes/namespace.yaml
echo "✅ Namespaces created"
```

---

### Step 8 — Deploy Redis

```bash
cat > kubernetes/redis.yaml << 'EOF'
apiVersion: apps/v1
kind: Deployment
metadata:
  name: redis
  namespace: url-shortener
  labels:
    app: redis
spec:
  replicas: 1
  selector:
    matchLabels:
      app: redis
  template:
    metadata:
      labels:
        app: redis
    spec:
      containers:
      - name: redis
        image: redis:7-alpine
        ports:
        - containerPort: 6379
        resources:
          requests:
            memory: "64Mi"
            cpu: "50m"
          limits:
            memory: "128Mi"
            cpu: "250m"
        livenessProbe:
          exec:
            command: ["redis-cli", "ping"]
          initialDelaySeconds: 10
          periodSeconds: 5
        readinessProbe:
          exec:
            command: ["redis-cli", "ping"]
          initialDelaySeconds: 5
          periodSeconds: 3
---
apiVersion: v1
kind: Service
metadata:
  name: redis
  namespace: url-shortener
  labels:
    app: redis
spec:
  selector:
    app: redis
  ports:
  - name: redis
    port: 6379
    targetPort: 6379
  type: ClusterIP
EOF

kubectl apply -f kubernetes/redis.yaml

kubectl wait \
  --for=condition=Ready \
  pods -l app=redis \
  -n url-shortener \
  --timeout=120s

echo "✅ Redis ready"
```

---

### Step 9 — Deploy the Application

```bash
cat > kubernetes/app.yaml << 'EOF'
apiVersion: apps/v1
kind: Deployment
metadata:
  name: url-shortener
  namespace: url-shortener
  labels:
    app: url-shortener
    version: v1
spec:
  replicas: 2
  selector:
    matchLabels:
      app: url-shortener
  template:
    metadata:
      labels:
        app: url-shortener
        version: v1
      annotations:
        # Prometheus auto-discovery annotations
        # Prometheus watches for these and scrapes automatically
        prometheus.io/scrape: "true"
        prometheus.io/path: "/metrics"
        prometheus.io/port: "8000"
    spec:
      containers:
      - name: app
        image: url-shortener:observable
        imagePullPolicy: Never
        ports:
        - containerPort: 8000
          name: http
        env:
        - name: REDIS_HOST
          value: "redis"
        - name: REDIS_PORT
          value: "6379"
        - name: LOG_LEVEL
          value: "info"
        - name: APP_VERSION
          value: "1.0.0"
        # Kubernetes Downward API — inject pod metadata as env vars
        # Used in structured logs to identify which pod handled request
        - name: POD_NAME
          valueFrom:
            fieldRef:
              fieldPath: metadata.name
        - name: POD_NAMESPACE
          valueFrom:
            fieldRef:
              fieldPath: metadata.namespace
        - name: NODE_NAME
          valueFrom:
            fieldRef:
              fieldPath: spec.nodeName
        resources:
          requests:
            memory: "128Mi"
            cpu: "100m"
          limits:
            memory: "256Mi"
            cpu: "500m"
        livenessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 15
          periodSeconds: 10
          failureThreshold: 3
        readinessProbe:
          httpGet:
            path: /ready
            port: 8000
          initialDelaySeconds: 5
          periodSeconds: 5
          failureThreshold: 3
---
apiVersion: v1
kind: Service
metadata:
  name: url-shortener
  namespace: url-shortener
  labels:
    app: url-shortener
spec:
  selector:
    app: url-shortener
  ports:
  - name: http
    port: 80
    targetPort: 8000
  type: ClusterIP
---
apiVersion: v1
kind: Service
metadata:
  name: url-shortener-external
  namespace: url-shortener
spec:
  selector:
    app: url-shortener
  ports:
  - name: http
    port: 80
    targetPort: 8000
    nodePort: 30080
  type: NodePort
EOF

kubectl apply -f kubernetes/app.yaml

kubectl wait \
  --for=condition=Ready \
  pods -l app=url-shortener \
  -n url-shortener \
  --timeout=120s

echo ""
echo "=== App Pods ==="
kubectl get pods -n url-shortener

# Test the app
MINIKUBE_IP=$(minikube ip)
curl -s http://$MINIKUBE_IP:30080/health | python3 -m json.tool
```

---

### Step 10 — Verify Metrics Endpoint

```bash
MINIKUBE_IP=$(minikube ip)

echo "=== Raw Prometheus Metrics ==="
curl -s http://$MINIKUBE_IP:30080/metrics | head -40

echo ""
echo "=== Specific Metrics ==="
curl -s http://$MINIKUBE_IP:30080/metrics | grep "http_requests_total"
curl -s http://$MINIKUBE_IP:30080/metrics | grep "redis_connected"
curl -s http://$MINIKUBE_IP:30080/metrics | grep "urls_shortened_total"
```

You should see output like:
```
# HELP http_requests_total Total HTTP requests
# TYPE http_requests_total counter
http_requests_total{endpoint="/health",method="GET",status_code="200"} 3.0
# HELP redis_connected Redis status: 1=up, 0=down
redis_connected 1.0
```

---

### Step 11 — Install Prometheus Stack

```bash
# Add the Helm repository
helm repo add prometheus-community \
  https://prometheus-community.github.io/helm-charts
helm repo update

# Create Prometheus values configuration
cat > monitoring/prometheus/values.yaml << 'EOF'
prometheus:
  prometheusSpec:
    retention: 15d
    retentionSize: 5GiB
    scrapeInterval: 15s
    evaluationInterval: 15s
    # Auto-discover pods with prometheus.io/scrape: "true" annotation
    additionalScrapeConfigs:
    - job_name: 'kubernetes-pods'
      kubernetes_sd_configs:
      - role: pod
        namespaces:
          names:
          - url-shortener
      relabel_configs:
      - source_labels:
          - __meta_kubernetes_pod_annotation_prometheus_io_scrape
        action: keep
        regex: true
      - source_labels:
          - __meta_kubernetes_pod_annotation_prometheus_io_path
        action: replace
        target_label: __metrics_path__
        regex: (.+)
      - source_labels:
          - __address__
          - __meta_kubernetes_pod_annotation_prometheus_io_port
        action: replace
        regex: ([^:]+)(?::\d+)?;(\d+)
        replacement: $1:$2
        target_label: __address__
      - action: labelmap
        regex: __meta_kubernetes_pod_label_(.+)
      - source_labels: [__meta_kubernetes_namespace]
        target_label: kubernetes_namespace
      - source_labels: [__meta_kubernetes_pod_name]
        target_label: kubernetes_pod_name

grafana:
  enabled: true
  adminPassword: "admin123"
  service:
    type: NodePort
    nodePort: 30030
  additionalDataSources:
  - name: Loki
    type: loki
    url: http://loki.monitoring.svc.cluster.local:3100
    access: proxy
    isDefault: false

alertmanager:
  enabled: true

nodeExporter:
  enabled: true

kubeStateMetrics:
  enabled: true

defaultRules:
  create: true
EOF

echo "Installing Prometheus stack (3-5 minutes)..."

helm install prometheus \
  prometheus-community/kube-prometheus-stack \
  --namespace monitoring \
  --values monitoring/prometheus/values.yaml \
  --wait \
  --timeout 10m

echo ""
echo "=== Monitoring Pods ==="
kubectl get pods -n monitoring

echo "✅ Prometheus stack installed"
```

---

### Step 12 — Create Custom Alert Rules

```bash
cat > monitoring/prometheus/alert-rules.yaml << 'EOF'
apiVersion: monitoring.coreos.com/v1
kind: PrometheusRule
metadata:
  name: url-shortener-alerts
  namespace: monitoring
  labels:
    release: prometheus
    app: kube-prometheus-stack
spec:
  groups:
  # Recording rules: pre-compute expensive queries for faster dashboards
  - name: url-shortener.recording
    interval: 30s
    rules:
    - record: job:http_requests:rate5m
      expr: |
        sum(rate(http_requests_total{kubernetes_namespace="url-shortener"}[5m]))
        by (endpoint, status_code)
    - record: job:http_error_rate:rate5m
      expr: |
        100 * sum(rate(http_requests_total{
          kubernetes_namespace="url-shortener", status_code=~"5.."
        }[5m])) /
        sum(rate(http_requests_total{kubernetes_namespace="url-shortener"}[5m]))
    - record: job:http_request_duration_p99:rate5m
      expr: |
        histogram_quantile(0.99,
          sum(rate(http_request_duration_seconds_bucket{
            kubernetes_namespace="url-shortener"
          }[5m])) by (le, endpoint)
        )

  # Alerting rules: fire when conditions are met
  - name: url-shortener.alerts
    rules:
    - alert: HighErrorRate
      expr: |
        (sum(rate(http_requests_total{
          kubernetes_namespace="url-shortener", status_code=~"5.."
        }[5m])) /
        sum(rate(http_requests_total{kubernetes_namespace="url-shortener"}[5m]))) > 0.05
      for: 2m
      labels:
        severity: critical
        team: platform
      annotations:
        summary: "High error rate on url-shortener"
        description: "Error rate is {{ $value | humanizePercentage }} (threshold: 5%)"

    - alert: HighLatency
      expr: |
        histogram_quantile(0.99,
          sum(rate(http_request_duration_seconds_bucket{
            kubernetes_namespace="url-shortener"
          }[5m])) by (le)
        ) > 1.0
      for: 5m
      labels:
        severity: warning
        team: platform
      annotations:
        summary: "High p99 latency on url-shortener"
        description: "p99 latency is {{ $value | humanizeDuration }} (threshold: 1s)"

    - alert: RedisDown
      expr: |
        redis_connected{kubernetes_namespace="url-shortener"} == 0
      for: 1m
      labels:
        severity: critical
        team: platform
      annotations:
        summary: "Redis is unreachable from url-shortener"
        description: "The app cannot connect to Redis. All write operations will fail."

    - alert: PodCrashLooping
      expr: |
        rate(kube_pod_container_status_restarts_total{
          namespace="url-shortener"
        }[15m]) * 60 * 15 > 0
      for: 5m
      labels:
        severity: warning
      annotations:
        summary: "Pod {{ $labels.pod }} is crash-looping"
        description: "Pod has restarted {{ $value }} times in the last 15 minutes"

    - alert: HighMemoryUsage
      expr: |
        container_memory_working_set_bytes{
          namespace="url-shortener", container="app"
        } /
        container_spec_memory_limit_bytes{
          namespace="url-shortener", container="app"
        } > 0.85
      for: 5m
      labels:
        severity: warning
      annotations:
        summary: "High memory usage in {{ $labels.pod }}"
        description: "Using {{ $value | humanizePercentage }} of memory limit"
EOF

kubectl apply -f monitoring/prometheus/alert-rules.yaml

echo "=== PrometheusRules ==="
kubectl get prometheusrule -n monitoring

echo "✅ Alert rules created"
```

---

### Step 13 — Install Loki (Log Aggregation)

```bash
helm repo add grafana https://grafana.github.io/helm-charts
helm repo update

cat > monitoring/loki/values-fixed.yaml << 'EOF'
loki:
  enabled: true
  isDefault: false
  loki:
    auth_enabled: false
    commonConfig:
      replication_factor: 1
    storage:
      type: filesystem
    schemaConfig:
      configs:
      - from: "2024-01-01"
        store: tsdb
        object_store: filesystem
        schema: v13
        index:
          prefix: index_
          period: 24h
    limits_config:
      retention_period: 168h
      allow_structured_metadata: false
  singleBinary:
    replicas: 1
  deploymentMode: SingleBinary
  read:
    replicas: 0
  write:
    replicas: 0
  backend:
    replicas: 0
  gateway:
    enabled: false
  minio:
    enabled: false

promtail:
  enabled: true
  config:
    clients:
    - url: http://loki.monitoring.svc.cluster.local:3100/loki/api/v1/push
    server:
      http_listen_port: 3101
    positions:
      filename: /run/promtail/positions.yaml
    scrape_configs:
    - job_name: kubernetes-pods
      kubernetes_sd_configs:
      - role: pod
      pipeline_stages:
      - json:
          expressions:
            level: level
            service: service
            event: event
      - labels:
          level:
          service:
          event:
      relabel_configs:
      - source_labels: [__meta_kubernetes_namespace]
        action: keep
        regex: url-shortener|monitoring
      - source_labels: [__meta_kubernetes_namespace]
        target_label: namespace
      - source_labels: [__meta_kubernetes_pod_name]
        target_label: pod
      - source_labels: [__meta_kubernetes_pod_container_name]
        target_label: container
      - source_labels: [__meta_kubernetes_pod_label_app]
        target_label: app
      - source_labels:
          - __meta_kubernetes_pod_uid
          - __meta_kubernetes_pod_container_name
        target_label: __path__
        replacement: /var/log/pods/*$1*/$2/*.log
        separator: /

grafana:
  enabled: false
EOF

helm install loki \
  grafana/loki-stack \
  --namespace monitoring \
  --values monitoring/loki/values-fixed.yaml \
  --wait \
  --timeout 5m

echo ""
echo "=== Loki/Promtail Pods ==="
kubectl get pods -n monitoring | grep -E "loki|promtail"

echo "✅ Loki installed"
```

> **Troubleshooting Loki:** If Promtail shows `Ready: False` with a 500 error, see [Troubleshooting](#troubleshooting) section below.

---

### Step 14 — Install Jaeger (Distributed Tracing)

```bash
helm repo add jaegertracing https://jaegertracing.github.io/helm-charts
helm repo update

helm install jaeger \
  jaegertracing/jaeger \
  --namespace monitoring \
  --set provisionDataStore.cassandra=false \
  --set allInOne.enabled=true \
  --set storage.type=memory \
  --set agent.enabled=false \
  --set collector.enabled=false \
  --set query.enabled=false \
  --wait

echo ""
echo "=== Jaeger Pods ==="
kubectl get pods -n monitoring | grep jaeger

echo "✅ Jaeger installed"
```

---

### Step 15 — Grafana Dashboard as Code

```bash
# Create the dashboard JSON
cat > monitoring/grafana/dashboards/url-shortener.json << 'EOF'
{
  "dashboard": {
    "title": "URL Shortener — Golden Signals",
    "uid": "url-shortener-golden",
    "tags": ["url-shortener", "golden-signals"],
    "refresh": "30s",
    "time": {"from": "now-1h", "to": "now"},
    "panels": [
      {
        "id": 1, "title": "Request Rate (Traffic)",
        "type": "timeseries",
        "gridPos": {"h": 8, "w": 12, "x": 0, "y": 0},
        "targets": [{"expr": "sum(rate(http_requests_total{kubernetes_namespace='url-shortener'}[5m])) by (endpoint)", "legendFormat": "{{endpoint}}"}],
        "fieldConfig": {"defaults": {"unit": "reqps"}}
      },
      {
        "id": 2, "title": "Error Rate % (Errors)",
        "type": "timeseries",
        "gridPos": {"h": 8, "w": 12, "x": 12, "y": 0},
        "targets": [{"expr": "100 * sum(rate(http_requests_total{kubernetes_namespace='url-shortener', status_code=~'5..'}[5m])) / sum(rate(http_requests_total{kubernetes_namespace='url-shortener'}[5m]))", "legendFormat": "Error Rate %"}],
        "fieldConfig": {"defaults": {"unit": "percent"}}
      },
      {
        "id": 3, "title": "Latency p50/p95/p99 (Latency)",
        "type": "timeseries",
        "gridPos": {"h": 8, "w": 12, "x": 0, "y": 8},
        "targets": [
          {"expr": "histogram_quantile(0.50, sum(rate(http_request_duration_seconds_bucket{kubernetes_namespace='url-shortener'}[5m])) by (le))", "legendFormat": "p50"},
          {"expr": "histogram_quantile(0.95, sum(rate(http_request_duration_seconds_bucket{kubernetes_namespace='url-shortener'}[5m])) by (le))", "legendFormat": "p95"},
          {"expr": "histogram_quantile(0.99, sum(rate(http_request_duration_seconds_bucket{kubernetes_namespace='url-shortener'}[5m])) by (le))", "legendFormat": "p99"}
        ],
        "fieldConfig": {"defaults": {"unit": "s"}}
      },
      {
        "id": 4, "title": "Memory Usage (Saturation)",
        "type": "timeseries",
        "gridPos": {"h": 8, "w": 12, "x": 12, "y": 8},
        "targets": [{"expr": "container_memory_working_set_bytes{namespace='url-shortener', container='app'}", "legendFormat": "{{pod}}"}],
        "fieldConfig": {"defaults": {"unit": "bytes"}}
      },
      {
        "id": 5, "title": "URLs Shortened (Business KPI)",
        "type": "stat",
        "gridPos": {"h": 4, "w": 6, "x": 0, "y": 16},
        "targets": [{"expr": "sum(urls_shortened_total)"}]
      },
      {
        "id": 6, "title": "Redis Status",
        "type": "stat",
        "gridPos": {"h": 4, "w": 6, "x": 6, "y": 16},
        "targets": [{"expr": "redis_connected{kubernetes_namespace='url-shortener'}"}]
      }
    ],
    "schemaVersion": 38, "version": 1
  },
  "overwrite": true
}
EOF

# Wrap in a ConfigMap so Grafana auto-imports it
cat > monitoring/grafana/dashboards/configmap.yaml << 'CMEOF'
apiVersion: v1
kind: ConfigMap
metadata:
  name: url-shortener-dashboard
  namespace: monitoring
  labels:
    grafana_dashboard: "1"
data:
  url-shortener.json: |
CMEOF

# Append the JSON indented (required for YAML embedding)
python3 << 'PYEOF'
with open('monitoring/grafana/dashboards/url-shortener.json') as f:
    dashboard = f.read()
with open('monitoring/grafana/dashboards/configmap.yaml', 'a') as f:
    for line in dashboard.split('\n'):
        f.write('    ' + line + '\n')
print("✅ Dashboard ConfigMap created")
PYEOF

kubectl apply -f monitoring/grafana/dashboards/configmap.yaml

echo "✅ Grafana dashboard created as code"
```

---

### Step 16 — Configure Alertmanager

```bash
cat > monitoring/alertmanager/config.yaml << 'EOF'
apiVersion: v1
kind: Secret
metadata:
  name: alertmanager-prometheus-kube-prometheus-alertmanager
  namespace: monitoring
stringData:
  alertmanager.yaml: |
    global:
      resolve_timeout: 5m

    route:
      group_by: ['alertname', 'namespace', 'service']
      group_wait: 30s
      group_interval: 5m
      repeat_interval: 4h
      receiver: 'default'
      routes:
      - match:
          severity: critical
        receiver: slack-critical
        repeat_interval: 1h
      - match:
          severity: warning
        receiver: slack-warning

    receivers:
    - name: 'default'
      slack_configs:
      - channel: '#alerts'
        send_resolved: true
        title: '{{ .GroupLabels.alertname }}'
        text: '{{ range .Alerts }}{{ .Annotations.description }}{{ end }}'

    - name: 'slack-critical'
      slack_configs:
      - channel: '#alerts-critical'
        send_resolved: true
        title: ':rotating_light: CRITICAL: {{ .GroupLabels.alertname }}'
        text: |
          {{ range .Alerts }}
          *Summary:* {{ .Annotations.summary }}
          *Description:* {{ .Annotations.description }}
          {{ end }}
        color: 'danger'

    - name: 'slack-warning'
      slack_configs:
      - channel: '#alerts'
        send_resolved: true
        title: ':warning: WARNING: {{ .GroupLabels.alertname }}'
        text: '{{ range .Alerts }}{{ .Annotations.description }}{{ end }}'
        color: 'warning'

    inhibit_rules:
    - source_match:
        severity: 'critical'
      target_match:
        severity: 'warning'
      equal: ['alertname', 'namespace']
EOF

kubectl apply -f monitoring/alertmanager/config.yaml

echo "✅ Alertmanager configured"
```

---

### Step 17 — Access Dashboards

```bash
MINIKUBE_IP=$(minikube ip)

# Expose Prometheus and Alertmanager via NodePort
kubectl patch svc prometheus-kube-prometheus-prometheus \
  -n monitoring \
  -p '{"spec":{"type":"NodePort","ports":[{"port":9090,"nodePort":30090,"targetPort":9090}]}}' \
  2>/dev/null || true

kubectl patch svc prometheus-kube-prometheus-alertmanager \
  -n monitoring \
  -p '{"spec":{"type":"NodePort","ports":[{"port":9093,"nodePort":30093,"targetPort":9093}]}}' \
  2>/dev/null || true

kubectl patch svc jaeger-query \
  -n monitoring \
  -p '{"spec":{"type":"NodePort","ports":[{"port":16686,"nodePort":30686,"targetPort":16686}]}}' \
  2>/dev/null || true

echo ""
echo "╔══════════════════════════════════════════════════════╗"
echo "║           Dashboard Access                           ║"
echo "╠══════════════════════════════════════════════════════╣"
echo "║  App:         http://$MINIKUBE_IP:30080             ║"
echo "║  Grafana:     http://$MINIKUBE_IP:30030             ║"
echo "║               Username: admin  Password: admin123   ║"
echo "║  Prometheus:  http://$MINIKUBE_IP:30090             ║"
echo "║  Alertmanager:http://$MINIKUBE_IP:30093             ║"
echo "║  Jaeger:      http://$MINIKUBE_IP:30686             ║"
echo "╚══════════════════════════════════════════════════════╝"
```

#### Accessing from an EC2 Instance

If you are running Minikube on an EC2 instance and want to access dashboards from your laptop browser, use an SSH tunnel:

```bash
# Run this command ON YOUR LAPTOP (replace with your EC2 IP)
ssh -L 30030:MINIKUBE_IP:30030 \
    -L 30080:MINIKUBE_IP:30080 \
    -L 30090:MINIKUBE_IP:30090 \
    -L 30686:MINIKUBE_IP:30686 \
    -N ubuntu@your-ec2-public-ip

# Then open in your laptop browser:
# Grafana:    http://localhost:30030
# App:        http://localhost:30080
# Prometheus: http://localhost:30090
# Jaeger:     http://localhost:30686
```

To find `MINIKUBE_IP` on EC2:
```bash
minikube ip
```

---

### Step 18 — Generate Traffic

```bash
cat > scripts/generate-traffic.sh << 'EOF'
#!/bin/bash
BASE_URL=${1:-http://localhost:30080}
DURATION=${2:-120}
echo "Generating traffic to $BASE_URL for ${DURATION}s"
echo "Watch Grafana dashboards while this runs!"
echo ""

END=$(($(date +%s) + DURATION))
COUNT=0
CODES=()

while [ $(date +%s) -lt $END ]; do
  COUNT=$((COUNT + 1))
  RESPONSE=$(curl -sf -X POST "$BASE_URL/shorten" \
    -H "Content-Type: application/json" \
    -d "{\"url\":\"https://example-$COUNT.com/path?q=$RANDOM\"}" \
    --max-time 5 2>/dev/null)
  CODE=$(echo $RESPONSE | python3 -c \
    "import sys,json
try: print(json.load(sys.stdin)['short_code'])
except: print('')" 2>/dev/null)
  if [ -n "$CODE" ]; then
    CODES+=($CODE)
    echo "  [$COUNT] Shortened → $CODE"
    curl -sf -o /dev/null "$BASE_URL/r/$CODE" 2>/dev/null
    curl -sf -o /dev/null "$BASE_URL/stats/$CODE" 2>/dev/null
  fi
  curl -sf -o /dev/null "$BASE_URL/health" 2>/dev/null
  if [ ${#CODES[@]} -gt 0 ]; then
    RC=${CODES[$RANDOM % ${#CODES[@]}]}
    curl -sf -o /dev/null "$BASE_URL/r/$RC" 2>/dev/null
  fi
  # Simulate some 404s
  curl -sf -o /dev/null "$BASE_URL/r/invalid" 2>/dev/null
  sleep 1
done
echo ""
echo "✅ Done. Shortened $COUNT URLs."
EOF

chmod +x scripts/generate-traffic.sh

MINIKUBE_IP=$(minikube ip)

# Run traffic generation in background
./scripts/generate-traffic.sh "http://$MINIKUBE_IP:30080" 120 &
TRAFFIC_PID=$!

echo "Traffic running (PID: $TRAFFIC_PID)"
echo "Open Grafana now to see live metrics"
echo "Kill with: kill $TRAFFIC_PID"
```

---

### Step 19 — PromQL Queries to Try

Open Prometheus at `http://MINIKUBE_IP:30090` and try these queries:

```promql
# ── Traffic ──────────────────────────────────────────────────
# Total requests per second
sum(rate(http_requests_total[5m]))

# RPS broken down by endpoint
sum(rate(http_requests_total[5m])) by (endpoint)

# ── Errors ───────────────────────────────────────────────────
# Error rate as percentage
100 * sum(rate(http_requests_total{status_code=~"5.."}[5m]))
    / sum(rate(http_requests_total[5m]))

# ── Latency ──────────────────────────────────────────────────
# p50 latency
histogram_quantile(0.50,
  sum(rate(http_request_duration_seconds_bucket[5m])) by (le)
)

# p99 latency (your worst users)
histogram_quantile(0.99,
  sum(rate(http_request_duration_seconds_bucket[5m])) by (le)
)

# ── Saturation ───────────────────────────────────────────────
# Memory usage per pod
container_memory_working_set_bytes{
  namespace="url-shortener", container="app"
}

# CPU usage per pod
rate(container_cpu_usage_seconds_total{
  namespace="url-shortener", container="app"
}[5m])

# ── Business Metrics ─────────────────────────────────────────
# Total URLs shortened
sum(urls_shortened_total)

# URLs shortened per minute
sum(rate(urls_shortened_total[1m])) * 60

# Redis health (1=up, 0=down)
redis_connected
```

---

### Step 20 — Loki Log Queries

In Grafana, go to **Explore → Select Loki datasource** and try:

```logql
# All logs from url-shortener
{namespace="url-shortener"}

# Error logs only
{namespace="url-shortener"} | json | level="ERROR"

# Slow requests (> 500ms)
{namespace="url-shortener"} | json | duration_ms > 500

# URL shortening events
{namespace="url-shortener"} | json | event="url_shortened"

# Specific request ID (trace a single request)
{namespace="url-shortener"} | json | request_id="abc12345"

# Log rate chart
rate({namespace="url-shortener"}[1m])
```

---

### Step 21 — Final Verification

```bash
cd ~/projects/day38-observability
MINIKUBE_IP=$(minikube ip)
BASE_URL="http://$MINIKUBE_IP:30080"

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  DAY 38 FINAL VERIFICATION"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

PASS=0; FAIL=0
check() {
  local name=$1 result=$2
  if [ "$result" = "pass" ]; then
    echo "  ✅ $name"; PASS=$((PASS+1))
  else
    echo "  ❌ $name"; FAIL=$((FAIL+1))
  fi
}

echo ""
echo "=== Application ==="
HEALTH=$(curl -sf --max-time 10 "$BASE_URL/health" 2>/dev/null || echo "{}")
check "Health endpoint: healthy"  "$(echo $HEALTH | grep -q healthy && echo pass || echo fail)"
check "Health endpoint: redis"    "$(echo $HEALTH | grep -q connected && echo pass || echo fail)"

METRICS=$(curl -sf --max-time 10 "$BASE_URL/metrics" 2>/dev/null || echo "")
check "Prometheus metrics exposed"  "$(echo $METRICS | grep -q http_requests_total && echo pass || echo fail)"
check "Business metric exposed"     "$(echo $METRICS | grep -q urls_shortened_total && echo pass || echo fail)"
check "Redis gauge exposed"         "$(echo $METRICS | grep -q redis_connected && echo pass || echo fail)"

echo ""
echo "=== Monitoring Stack ==="
PROM=$(kubectl get pods -n monitoring -l app.kubernetes.io/name=prometheus \
  --field-selector=status.phase=Running --no-headers 2>/dev/null | wc -l)
check "Prometheus running"  "$([ $PROM -ge 1 ] && echo pass || echo fail)"

GRAFANA=$(kubectl get pods -n monitoring -l app.kubernetes.io/name=grafana \
  --field-selector=status.phase=Running --no-headers 2>/dev/null | wc -l)
check "Grafana running"  "$([ $GRAFANA -ge 1 ] && echo pass || echo fail)"

LOKI=$(kubectl get pods -n monitoring -l app=loki \
  --field-selector=status.phase=Running --no-headers 2>/dev/null | wc -l)
check "Loki running"  "$([ $LOKI -ge 1 ] && echo pass || echo fail)"

JAEGER=$(kubectl get pods -n monitoring -l app.kubernetes.io/name=jaeger \
  --field-selector=status.phase=Running --no-headers 2>/dev/null | wc -l)
check "Jaeger running"  "$([ $JAEGER -ge 1 ] && echo pass || echo fail)"

echo ""
echo "=== Alerting ==="
RULES=$(kubectl get prometheusrule -n monitoring --no-headers 2>/dev/null | wc -l)
check "PrometheusRule created"  "$([ $RULES -ge 1 ] && echo pass || echo fail)"

echo ""
echo "=== End-to-End Flow ==="
SHORTEN=$(curl -sf -X POST "$BASE_URL/shorten" \
  -H "Content-Type: application/json" \
  -d '{"url":"https://kubernetes.io"}' 2>/dev/null || echo "{}")
CODE=$(echo $SHORTEN | python3 -c \
  "import sys,json; print(json.load(sys.stdin).get('short_code',''))" 2>/dev/null)
check "URL shortening works"  "$([ -n '$CODE' ] && echo pass || echo fail)"
if [ -n "$CODE" ]; then
  REDIR=$(curl -sf -o /dev/null -w "%{http_code}" "$BASE_URL/r/$CODE" 2>/dev/null)
  check "Redirect works (HTTP $REDIR)"  "$(echo $REDIR | grep -q '^3' && echo pass || echo fail)"
fi

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  Results: $PASS passed | $FAIL failed"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "Dashboard URLs (if SSH tunnel is running):"
echo "  Grafana:    http://localhost:30030  (admin / admin123)"
echo "  Prometheus: http://localhost:30090"
echo "  Jaeger:     http://localhost:30686"
```

---

## Key Concepts Explained

### Why JSON Logs?

Plain text logs require regex to extract fields for analysis. JSON logs make every field directly queryable in Loki:

```logql
# Filter by structured field (no regex needed)
{namespace="url-shortener"} | json | duration_ms > 500
```

### Why Histogram Over Average for Latency?

```
Average: "requests take 50ms on average"
         Hides the fact that 1% take 10 seconds

p99:     "99% of requests complete in under 200ms"
         The 1% taking 10 seconds = 1 in 100 users
         At 1000 req/s = 10 users/s experiencing 10s waits
```

### Why Path Normalization Matters

Without normalization, each unique short code creates a separate Prometheus time series:

```
/r/abc123 → 1 time series
/r/def456 → 1 time series
/r/xyz789 → 1 time series
...1000 codes = 1000 time series (kills Prometheus memory)

With normalization:
/r/{code} → 1 time series (always)
```

### Why Dashboards as Code?

Dashboards stored in Grafana's SQLite are lost when the pod restarts. ConfigMaps backed by etcd persist. This approach makes dashboards version-controlled and reproducible.

---

## Troubleshooting

### Promtail Not Ready (HTTP 500)

This is a known issue with Promtail 3.x and the loki-stack chart:

```bash
# Check Promtail logs
kubectl logs -l app.kubernetes.io/name=promtail -n monitoring --tail=30

# Fix: uninstall and reinstall with corrected values
helm uninstall loki -n monitoring
sleep 15

# Reinstall with values-fixed.yaml (already created in Step 13)
helm install loki grafana/loki-stack \
  --namespace monitoring \
  --values monitoring/loki/values-fixed.yaml \
  --wait --timeout 5m
```

### App Pods Not Starting

```bash
# Check pod events
kubectl describe pods -l app=url-shortener -n url-shortener | tail -20

# Common cause: image not found in minikube
# Solution: ensure you built inside minikube's Docker
eval $(minikube docker-env)
docker images | grep url-shortener

# If image is missing, rebuild
docker build -t url-shortener:observable .
```

### Prometheus Not Scraping App

```bash
# Check Prometheus targets
curl -s "http://$(minikube ip):30090/api/v1/targets" | \
  python3 -m json.tool | grep -A5 "url-shortener"

# Verify annotations are on the pod
kubectl get pod -l app=url-shortener -n url-shortener \
  -o jsonpath='{.items[0].metadata.annotations}' | python3 -m json.tool
```

### Grafana Cannot Connect to Loki

```bash
# Verify Loki service exists
kubectl get svc -n monitoring | grep loki

# Test Loki readiness
kubectl port-forward svc/loki 3100:3100 -n monitoring &
sleep 3
curl -s http://localhost:3100/ready
kill %1
```

### Minikube Out of Memory

```bash
# Stop and restart with more memory
minikube stop
minikube delete
minikube start --driver=docker --memory=8192 --cpus=4

# Then rebuild the image and redeploy
eval $(minikube docker-env)
docker build -t url-shortener:observable .
kubectl apply -f kubernetes/
```

---

## Interview Q&A

**Q: What is observability and how is it different from monitoring?**
> Monitoring watches predefined metrics and alerts on known failure modes. Observability lets you investigate unknown failures — you can ask any question about system state using metrics, logs, and traces as raw material. Monitoring tells you *something is wrong*. Observability tells you *why*.

**Q: What are the four golden signals?**
> Traffic (requests/second), Errors (% of requests failing), Latency (response time percentiles — p50/p95/p99, never average), and Saturation (how full the system is — CPU%, memory%, queue depth). These four signals give a complete picture of service health.

**Q: Why use p99 latency instead of average?**
> Average hides tail latency. If 99% of requests take 10ms and 1% take 10 seconds, the average might be 110ms — which looks fine. But at 1000 req/s, that 1% means 10 users/second waiting 10 seconds. p99 directly represents your worst-user experience.

**Q: What is high cardinality and why is it a problem in Prometheus?**
> Cardinality is the number of unique time series. Each unique label value combination creates a separate time series stored in memory. If you label by user_id with 1 million users, that's 1 million time series per metric, causing OOM crashes. Good labels have low cardinality: HTTP method (5 values), endpoint (10-20 values), status code (10-15 values).

**Q: What is the difference between a recording rule and an alerting rule?**
> Recording rules pre-compute expensive PromQL queries on a schedule and store results as new metrics. Dashboard panels query the pre-computed metric (fast) instead of running the expensive query live (slow). Alerting rules fire when a condition is true for a specified duration (`for: 2m`), preventing noise from brief spikes.

**Q: How does Prometheus discover what to scrape in Kubernetes?**
> Via service discovery and relabeling. Prometheus watches the Kubernetes API for pods. The relabeling config keeps only pods with `prometheus.io/scrape: "true"` annotation. The scrape path and port come from `prometheus.io/path` and `prometheus.io/port` annotations. No manual registration needed — annotate your pod and Prometheus finds it automatically.

---

## Cleanup

```bash
# Remove the application
helm uninstall url-shortener -n url-shortener 2>/dev/null || true
kubectl delete -f kubernetes/ 2>/dev/null || true

# Remove monitoring stack
helm uninstall prometheus -n monitoring 2>/dev/null || true
helm uninstall loki -n monitoring 2>/dev/null || true
helm uninstall jaeger -n monitoring 2>/dev/null || true
kubectl delete -f monitoring/ --recursive 2>/dev/null || true

# Stop Minikube
minikube stop

# Delete Minikube (frees all disk space)
minikube delete
```

---

## Resources

- [Prometheus Documentation](https://prometheus.io/docs/)
- [Grafana Documentation](https://grafana.com/docs/)
- [Loki Documentation](https://grafana.com/docs/loki/)
- [Jaeger Documentation](https://www.jaegertracing.io/docs/)
- [Google SRE Book — Golden Signals](https://sre.google/sre-book/monitoring-distributed-systems/)
- [PromQL Cheat Sheet](https://promlabs.com/promql-cheat-sheet/)
- [LogQL Cheat Sheet](https://grafana.com/docs/loki/latest/query/)
