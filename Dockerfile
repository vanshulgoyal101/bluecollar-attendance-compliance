# Production image for the Workforce Attendance Compliance app.
# Serves the Flask API + dashboard via gunicorn (threaded workers for SSE).
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=5001

WORKDIR /app

# Install dependencies first for better layer caching.
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Copy the application source.
COPY . .

# Drop root for runtime.
RUN useradd --create-home --uid 10001 appuser \
    && chown -R appuser:appuser /app
USER appuser

EXPOSE 5001

# Basic container healthcheck against the public liveness endpoint.
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD python -c "import os,urllib.request,sys; \
url='http://127.0.0.1:%s/api/health' % os.getenv('PORT','5001'); \
sys.exit(0 if urllib.request.urlopen(url, timeout=2).status==200 else 1)"

CMD ["gunicorn", "-c", "gunicorn.conf.py", "wsgi:app"]
