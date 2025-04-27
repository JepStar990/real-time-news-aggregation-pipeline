# rss_feeder/health.py
from fastapi import FastAPI, HTTPException
from typing import Dict, Any
from datetime import datetime
import psutil
import socket

app = FastAPI()

def get_system_stats() -> Dict[str, Any]:
    """Collect system health metrics"""
    return {
        "timestamp": datetime.utcnow().isoformat(),
        "cpu_percent": psutil.cpu_percent(),
        "memory_usage": psutil.virtual_memory().percent,
        "disk_usage": psutil.disk_usage('/').percent,
        "hostname": socket.gethostname()
    }

@app.get("/health")
async def health_check() -> Dict:
    """Basic health endpoint"""
    try:
        stats = get_system_stats()
        return {
            "status": "healthy",
            "system": stats,
            "services": {
                "kafka": True,  # TODO: Add actual check
                "scheduler": True  # TODO: Add actual check
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/metrics")
async def metrics() -> Dict:
    """Detailed metrics endpoint"""
    try:
        stats = get_system_stats()
        # Add scheduler-specific metrics
        stats.update({
            "feed_count": len(feed_manager.load_feeds()),
            "active_jobs": len(scheduler.scheduler.get_jobs()),
            "next_run_time": str(scheduler.scheduler.next_run_time)
        })
        return stats
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Note: The scheduler and feed_manager instances need to be injected
# from the main application
