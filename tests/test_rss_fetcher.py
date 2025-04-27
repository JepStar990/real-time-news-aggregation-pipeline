# tests/test_rss_fetcher.py
import pytest
from unittest.mock import MagicMock, patch
from rss_feeder.rss_fetcher import RSSFetcher
from rss_feeder import config

@pytest.fixture
def rss_fetcher():
    with patch('rss_feeder.rss_fetcher.StorageManager'), \
         patch('rss_feeder.rss_fetcher.Validator'), \
         patch('rss_feeder.rss_fetcher.KafkaPublisher'):
        return RSSFetcher()

def test_fetch_feed_success(rss_fetcher):
    """Test successful feed fetch"""
    with patch('requests.get') as mock_get:
        mock_get.return_value.status_code = 200
        mock_get.return_value.headers = {}
        mock_get.return_value.content = b'<rss>content</rss>'
        
        result = rss_fetcher.fetch_feed("http://test.com", "TestFeed")
        assert result is not None
        assert mock_get.call_count == 1

def test_fetch_feed_not_modified(rss_fetcher):
    """Test handling of 304 Not Modified"""
    with patch('requests.get') as mock_get:
        mock_get.return_value.status_code = 304
        result = rss_fetcher.fetch_feed("http://test.com", "TestFeed")
        assert result is None

def test_process_feeds(rss_fetcher):
    """Test feed processing"""
    mock_fm = MagicMock()
    mock_fm.load_feeds.return_value = [
        {"name": "Feed1", "url": "http://feed1.com"}
    ]
    
    with patch('rss_feeder.rss_fetcher.FeedManager', return_value=mock_fm), \
         patch.object(rss_fetcher, 'fetch_feed', return_value={"entries": []}):
        rss_fetcher.process_feeds()
        rss_fetcher.fetch_feed.assert_called_once()

def test_is_duplicate(rss_fetcher):
    """Test duplicate URL detection"""
    url = "http://test.com"
    assert rss_fetcher._is_duplicate(url) is False
    assert rss_fetcher._is_duplicate(url) is True  # Now should be duplicate
