from prometheus_client import Gauge, Histogram

# Gauge to track currently connected WebSocket clients
websocket_connected_clients = Gauge(
    "websocket_connected_clients",
    "Number of active WebSocket clients connected to room channels"
)

# Histogram to track database query duration in seconds
db_query_duration_seconds = Histogram(
    "db_query_duration_seconds",
    "Duration of database query execution in seconds",
    buckets=(0.001, 0.005, 0.01, 0.025, 0.05, 0.075, 0.1, 0.25, 0.5, 0.75, 1.0, 2.5, 5.0, 10.0)
)
