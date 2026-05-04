# Multi-stage build
FROM python:3.12-slim AS builder

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt --target=/install

FROM python:3.12-slim

WORKDIR /app

COPY --from=builder /install /usr/local/lib/python3.12/site-packages

COPY ./rss_feeder /app/rss_feeder
COPY ./rss_feeder/logging.conf /app/rss_feeder/logging.conf

ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1

EXPOSE 8000

RUN useradd --create-home --shell /bin/bash appuser
USER appuser

CMD ["uvicorn", "rss_feeder.__main__:app", "--host", "0.0.0.0", "--port", "8000", "--log-level", "info"]
