from fastapi import FastAPI, Depends, HTTPException, Security
from fastapi.security import APIKeyHeader
from fastapi.middleware.cors import CORSMiddleware
from typing import Dict, Any
import psutil
import os
import logging
from prometheus_client import make_asgi_app, Counter, Gauge, Histogram
from pydantic import BaseModel
import httpx
from datetime import datetime, timedelta

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

# Add Prometheus metrics
metrics_app = make_asgi_app()
app.mount("/metrics", metrics_app)

# CORS Configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def verify_api_key(api_key: str = Security(api_key_header)):
    """Validate API key against environment variable"""
    if api_key != os.getenv("API_KEY"):
        raise HTTPException(status_code=403, detail="Invalid API Key")

@app.on_event("startup")
async def startup_event():
    """Initialize monitoring metrics"""
    FEED_GAUGE.set(len(feed_manager.load_feeds()))

async def check_kafka() -> bool:
    """Verify Kafka connectivity"""
    try:
        async with httpx.AsyncClient() as client:
            res = await client.get(f"http://{os.getenv('KAFKA_BROKER_URL')}/")
            return res.status_code == 200
    except Exception:
        return False

async def check_scheduler(scheduler) -> Dict[str, Any]:
    """Get scheduler health metrics"""
    return {
        "active_jobs": len(scheduler.scheduler.get_jobs()),
        "next_run": str(scheduler.scheduler.next_run_time),
        "pending_jobs": len(scheduler.scheduler.get_jobs(pending=True))
    }

# Function to get the scheduler instance
def get_scheduler():
    # Import your main application to access the scheduler
    from rss_feeder.__main__ import Application
    return Application().scheduler

@app.get("/health", response_model=HealthStatus)
async def health_check(scheduler: Any = Depends(get_scheduler)) -> Dict:
    """Comprehensive health endpoint"""
    with REQUEST_LATENCY.labels("/health").time():
        REQUEST_COUNT.labels("/health", "GET").inc()
        try:
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
                        "raw_feeds": len(os.listdir(config.RAW_FEEDS_DIR)),
                        "parsed_articles": len(os.listdir(config.PARSED_ARTICLES_DIR))
                    }
                }
            }

            status = "healthy" if all(stats["services"].values()) else "degraded"

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
