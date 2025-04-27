# tests/test_health.py
import pytest
from fastapi.testclient import TestClient
from rss_feeder.health import app, get_system_stats
from unittest.mock import patch

@pytest.fixture
def client():
    return TestClient(app)

def test_health_endpoint(client):
    """Test health endpoint"""
    with patch('rss_feeder.health.get_system_stats') as mock_stats:
        mock_stats.return_value = {"cpu_percent": 10}
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json()["status"] == "healthy"

def test_metrics_endpoint(client):
    """Test metrics endpoint"""
    with patch('rss_feeder.health.get_system_stats') as mock_stats, \
         patch('rss_feeder.health.feed_manager') as mock_fm, \
         patch('rss_feeder.health.scheduler') as mock_scheduler:
        
        mock_stats.return_value = {"cpu_percent": 10}
        mock_fm.load_feeds.return_value = [{"name": "Feed1"}]
        mock_scheduler.scheduler.get_jobs.return_value = [MagicMock()]
        mock_scheduler.scheduler.next_run_time = "2023-01-01"
        
        response = client.get("/metrics")
        assert response.status_code == 200
        data = response.json()
        assert data["cpu_percent"] == 10
        assert data["feed_count"] == 1

def test_health_error_handling(client):
    """Test error handling in health check"""
    with patch('rss_feeder.health.get_system_stats', side_effect=Exception("Test error")):
        response = client.get("/health")
        assert response.status_code == 500
