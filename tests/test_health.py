# tests/test_health.py
import pytest
from fastapi.testclient import TestClient
from rss_feeder.health import app
from unittest.mock import patch


@pytest.fixture
def client():
    return TestClient(app)


def test_health_endpoint(client):
    """Test health endpoint returns 200."""
    with patch('rss_feeder.health._get_scheduler', return_value=None), \
         patch('rss_feeder.health.check_kafka', return_value=True):
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] in ("healthy", "degraded")


def test_health_with_kafka_down(client):
    """Test health endpoint with Kafka down."""
    with patch('rss_feeder.health._get_scheduler', return_value=None), \
         patch('rss_feeder.health.check_kafka', return_value=False):
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json()["status"] == "degraded"


def test_health_error_handling(client):
    """Test error handling in health check."""
    with patch('rss_feeder.health.check_kafka', side_effect=Exception("Test error")), \
         patch('rss_feeder.health._get_scheduler', return_value=None):
        response = client.get("/health")
        assert response.status_code == 500


def test_metrics_endpoint_returns_data_without_key(client):
    """Test metrics/detailed endpoint is accessible (no API key set in env)."""
    with patch('rss_feeder.health._get_scheduler', return_value=None):
        response = client.get("/metrics/detailed")
        assert response.status_code == 200


def test_invalid_endpoint(client):
    """Test handling of invalid endpoint."""
    response = client.get("/invalid")
    assert response.status_code == 404
