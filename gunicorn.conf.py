"""Gunicorn configuration for the attendance compliance app.

Threaded workers are used because ``/api/chat/stream`` holds a request open for
the duration of an SSE response; a thread pool keeps other requests responsive
while a stream is in flight. Tune via env vars (WEB_CONCURRENCY, GUNICORN_THREADS,
PORT).
"""

import os

# Bind to all interfaces so the container is reachable; PORT overrides the port.
bind = f"0.0.0.0:{os.getenv('PORT', '5001')}"

# Threaded workers suit streaming (SSE) + mostly-I/O request handling.
workers = int(os.getenv("WEB_CONCURRENCY", "2"))
worker_class = "gthread"
threads = int(os.getenv("GUNICORN_THREADS", "8"))

# Streams can be long-lived; don't let the worker timeout kill them mid-response.
timeout = int(os.getenv("GUNICORN_TIMEOUT", "120"))
graceful_timeout = 30
keepalive = 5

# Log to stdout/stderr so container platforms capture them.
accesslog = "-"
errorlog = "-"
loglevel = os.getenv("GUNICORN_LOG_LEVEL", "info")
