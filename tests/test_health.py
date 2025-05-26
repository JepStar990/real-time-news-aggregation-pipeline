# tests/test_health.py
import pytest
from fastapi.testclient import TestClient
from rss_feeder.health import app
from unittest.mock import patch, MagicMock
import psutil
import os

@pytest.fixture
def client():
    return TestClient(app)

def test_health_endpoint(client):
    """Test health endpoint."""
    with patch('rss_feeder.health.get_system_stats') as mock_stats:
        mock_stats.return_value = {"cpu_percent": 10}
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json()["status"] == "healthy"

def test_health_with_kafka_down(client):
    """Test health endpoint with Kafka down."""
    with patch('rss_feeder.health.check_kafka', return_value=False), \
         patch('rss_feeder.health.get_system_stats', return_value={"cpu_percent": 10}):
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json()["status"] == "degraded"

def test_health_with_scheduler_down(client):
    """Test health endpoint with scheduler down."""
    with patch('rss_feeder.health.check_scheduler', return_value={"active_jobs": 0, "next_run": None, "pending_jobs": 0}), \
         patch('rss_feeder.health.get_system_stats', return_value={"cpu_percent": 10}):
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json()["status"] == "degraded"

def test_health_error_handling(client):
    """Test error handling in health check."""
    with patch('rss_feeder.health.get_system_stats', side_effect=Exception("Test error")):
        response = client.get("/health")
        assert response.status_code == 500

def test_metrics_endpoint(client):
    """Test metrics endpoint."""
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
        assert "articles_processed" in data  # Check for articles_processed in metrics
        assert "system" in data  # Ensure system metrics are present

def test_metrics_authentication(client):
    """Test metrics endpoint with missing API key."""
    response = client.get("/metrics")
    assert response.status_code == 403  # Forbidden due to missing API key

def test_metrics_with_invalid_api_key(client):
    """Test metrics endpoint with invalid API key."""
    with patch('rss_feeder.health.verify_api_key', side_effect=Exception("Invalid API Key")):
        response = client.get("/metrics", params={"api_key": "wrong_key"})
        assert response.status_code == 403  # Forbidden due to invalid API key

def test_metrics_with_valid_api_key(client):
    """Test metrics endpoint with valid API key."""
    with patch('rss_feeder.health.verify_api_key', return_value=None):
        response = client.get("/metrics", params={"api_key": os.getenv("API_KEY")})
        assert response.status_code == 200

def test_check_kafka_success(client):
    """Test Kafka connectivity check."""
    with patch('rss_feeder.health.check_kafka', return_value=True), \
         patch('rss_feeder.health.get_system_stats', return_value={"cpu_percent": 10}):
        response = client.get("/health")
        assert response.json()["services"]["kafka"] is True

def test_check_kafka_failure(client):
    """Test Kafka connectivity failure."""
    with patch('rss_feeder.health.check_kafka', return_value=False), \
         patch('rss_feeder.health.get_system_stats', return_value={"cpu_percent": 10}):
        response = client.get("/health")
        assert response.json()["services"]["kafka"] is False

def test_check_scheduler_success(client):
    """Test scheduler health check."""
    mock_scheduler = {
        "active_jobs": 1,
        "next_run": "2023-01-01",
        "pending_jobs": 0
    }
    with patch('rss_feeder.health.check_scheduler', return_value=mock_scheduler), \
         patch('rss_feeder.health.get_system_stats', return_value={"cpu_percent": 10}):
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json()["services"]["scheduler"]["active_jobs"] == 1

def test_check_scheduler_failure(client):
    """Test scheduler health check with no jobs."""
    mock_scheduler = {
        "active_jobs": 0,
        "next_run": None,
        "pending_jobs": 0
    }
    with patch('rss_feeder.health.check_scheduler', return_value=mock_scheduler), \
         patch('rss_feeder.health.get_system_stats', return_value={"cpu_percent": 10}):
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json()["services"]["scheduler"]["active_jobs"] == 0

def test_invalid_endpoint(client):
    """Test handling of invalid endpoint."""
    response = client.get("/invalid")
    assert response.status_code == 404  # Not Found
