# tests/test_rss_fetcher.py
import pytest
from unittest.mock import MagicMock, patch, AsyncMock
from rss_feeder.rss_fetcher import RSSFetcher
from rss_feeder import config


@pytest.fixture
def rss_fetcher():
    with patch('rss_feeder.rss_fetcher.StorageManager'), \
         patch('rss_feeder.rss_fetcher.Validator'), \
         patch('rss_feeder.rss_fetcher.KafkaPublisher'):
        fetcher = RSSFetcher()
        return fetcher


@pytest.mark.asyncio
async def test_fetch_feed_success(rss_fetcher):
    with patch.object(rss_fetcher, '_get_client') as mock_client_getter:
        mock_client = AsyncMock()
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.headers = {}
        mock_response.content = b'<rss>content</rss>'
        mock_client.get.return_value = mock_response
        mock_client_getter.return_value = mock_client

        result = await rss_fetcher.fetch_feed("http://test.com", "TestFeed")
        assert result is not None


@pytest.mark.asyncio
async def test_fetch_feed_not_modified(rss_fetcher):
    with patch.object(rss_fetcher, '_get_client') as mock_client_getter:
        mock_client = AsyncMock()
        mock_response = MagicMock()
        mock_response.status_code = 304
        mock_client.get.return_value = mock_response
        mock_client_getter.return_value = mock_client

        result = await rss_fetcher.fetch_feed("http://test.com", "TestFeed")
        assert result is None


def test_is_duplicate(rss_fetcher):
    url = "http://test.com/article1"
    assert rss_fetcher._is_duplicate(url) is False
    assert rss_fetcher._is_duplicate(url) is True


def test_lru_eviction(rss_fetcher):
    rss_fetcher.MAX_SEEN_URLS = 3
    for i in range(5):
        rss_fetcher._is_duplicate(f"http://test.com/{i}")
    # First URL should have been evicted
    assert rss_fetcher._is_duplicate("http://test.com/0") is False
    # Most recent URLs should still be tracked
    assert rss_fetcher._is_duplicate("http://test.com/4") is True
