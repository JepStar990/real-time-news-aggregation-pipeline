from fastapi import FastAPI, Depends, HTTPException, Security
from fastapi.security import APIKeyHeader
from fastapi.middleware.cors import CORSMiddleware
from typing import Dict, Any, Optional
import asyncio
import psutil
import os
import logging
from prometheus_client import make_asgi_app, Counter, Gauge, Histogram
from pydantic import BaseModel
import httpx
from datetime import datetime, timedelta

from rss_feeder import config
from rss_feeder.feed_manager import FeedManager

# Security
API_KEY_NAME = "X-API-KEY"
api_key_header = APIKeyHeader(name=API_KEY_NAME, auto_error=False)

# Metrics
METRICS_PREFIX = "rss_feeder_"
REQUEST_COUNT = Counter(f"{METRICS_PREFIX}request_count", "Total API requests", ["endpoint", "method"])
REQUEST_LATENCY = Histogram(f"{METRICS_PREFIX}request_latency_seconds", "Request latency", ["endpoint"])
FEED_GAUGE = Gauge(f"{METRICS_PREFIX}feeds_total", "Number of configured feeds")
PROCESSED_ARTICLES = Counter(f"{METRICS_PREFIX}articles_processed", "Articles processed", ["status"])

class HealthStatus(BaseModel):
    status: str
    details: Dict[str, Any]
    timestamp: str

app = FastAPI(title="RSS Feeder Health API",
              description="Monitoring and management endpoints",
              version="1.0.0")

metrics_app = make_asgi_app()
app.mount("/metrics", metrics_app)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def _get_scheduler():
    """Get the scheduler instance from the running application."""
    try:
        from rss_feeder.app_state import get_application
        app_instance = get_application()
        if app_instance and app_instance.scheduler:
            return app_instance.scheduler
    except Exception:
        pass
    return None

def verify_api_key(api_key: str = Security(api_key_header)):
    """Validate API key against environment variable."""
    expected_key = os.getenv("API_KEY")
    if not expected_key or api_key != expected_key:
        raise HTTPException(status_code=403, detail="Invalid API Key")

@app.on_event("startup")
async def startup_event():
    """Initialize monitoring metrics"""
    feed_manager = FeedManager()
    FEED_GAUGE.set(len(feed_manager.load_feeds()))

async def check_kafka() -> bool:
    """Verify Kafka connectivity via TCP socket."""
    import socket
    try:
        host, port = os.getenv('KAFKA_BROKER_URL', 'localhost:9092').split(':')
        _, writer = await asyncio.open_connection(host, int(port))
        writer.close()
        await writer.wait_closed()
        return True
    except Exception:
        return False

async def check_scheduler(scheduler) -> Dict[str, Any]:
    """Get scheduler health metrics"""
    if scheduler is None:
        return {"active_jobs": 0, "next_run": None, "pending_jobs": 0}
    try:
        jobs = scheduler.scheduler.get_jobs()
        next_run = None
        if jobs:
            next_run = str(min(job.next_run_time for job in jobs if job.next_run_time))
        return {
            "active_jobs": len(jobs),
            "next_run": next_run,
            "pending_jobs": len([j for j in jobs if getattr(j, 'pending', False)])
        }
    except Exception:
        return {"active_jobs": 0, "next_run": None, "pending_jobs": 0}

@app.get("/health", response_model=HealthStatus)
async def health_check() -> Dict:
    """Comprehensive health endpoint"""
    with REQUEST_LATENCY.labels("/health").time():
        REQUEST_COUNT.labels("/health", "GET").inc()
        try:
            scheduler = _get_scheduler()

            stats = {
                "system": {
                    "cpu": psutil.cpu_percent(),
                    "memory": psutil.virtual_memory().percent,
                    "disk": psutil.disk_usage('/').percent,
                    "uptime": timedelta(seconds=psutil.boot_time()).total_seconds()
                },
                "services": {
                    "kafka": await check_kafka(),
                    "scheduler": await check_scheduler(scheduler),
                    "storage": {
                        "raw_feeds": len(os.listdir(config.RAW_FEEDS_DIR)) if os.path.isdir(config.RAW_FEEDS_DIR) else 0,
                        "parsed_articles": len(os.listdir(config.PARSED_ARTICLES_DIR)) if os.path.isdir(config.PARSED_ARTICLES_DIR) else 0
                    }
                }
            }

            status = "healthy" if stats["services"]["kafka"] else "degraded"

            return HealthStatus(
                status=status,
                details=stats,
                timestamp=datetime.utcnow().isoformat()
            )
        except Exception as e:
            logging.error(f"Health check failed: {str(e)}")
            raise HTTPException(status_code=500, detail=str(e))

@app.get("/metrics/detailed")
async def detailed_metrics(api_key: str = Depends(verify_api_key)):
    """Advanced metrics with authentication"""
    return {
        "articles_processed": PROCESSED_ARTICLES._metrics.copy(),
        "system": {
            "cpu_cores": psutil.cpu_count(),
            "memory_total": psutil.virtual_memory().total
        }
    }
