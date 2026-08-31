"""
Prometheus metrics definitions for CineIQ API.
This module defines custom metrics for tracking API latency, error rates,
database query duration, and active WebSocket connections.
"""

from prometheus_client import Counter, Histogram, Gauge

# HTTP Requests Counter: Tracks total HTTP requests by method, path, and status code
http_requests_total = Counter(
    "http_requests_total", "Total number of HTTP requests", ["method", "path", "status"]
)

# HTTP Request Duration Histogram: Tracks latency distribution by route
http_request_duration_seconds = Histogram(
    "http_request_duration_seconds",
    "HTTP request duration in seconds",
    ["method", "path"],
    buckets=[0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0],
)

# Database Query Duration Histogram: Tracks SQLAlchemy query execution time
db_query_duration_seconds = Histogram(
    "db_query_duration_seconds",
    "Database query duration in seconds",
    buckets=[0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0],
)

# WebSocket Connected Clients Gauge: Tracks active real-time connections
websocket_connected_clients = Gauge(
    "websocket_connected_clients", "Number of currently connected WebSocket clients"
)
