FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY ./rss_feeder /app/rss_feeder
COPY ./rss_feeder/logging.conf /app/rss_feeder/logging.conf

ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1

EXPOSE 8000

RUN useradd --create-home --shell /bin/bash appuser \
    && mkdir -p /app/data/raw_feeds /app/data/parsed_articles /app/data/logs /app/outputs/articles /app/outputs/xmls /app/data/failed_articles \
    && chown -R appuser:appuser /app/data /app/outputs

USER appuser

CMD ["python", "-m", "rss_feeder"]
