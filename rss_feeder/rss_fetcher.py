# rss_feeder/rss_fetcher.py
import asyncio
import hashlib
import logging
import time
from collections import OrderedDict
from datetime import datetime
from typing import Dict, Optional, List

import feedparser
import httpx

from rss_feeder import config
from rss_feeder.feed_manager import FeedManager
from rss_feeder.storage_manager import StorageManager
from rss_feeder.validator import Validator
from rss_feeder.kafka_publisher import KafkaPublisher


class RSSFetcher:
    """Fetch and process RSS feeds with async connection pooling and activity tracking."""

    MAX_SEEN_URLS = 100_000  # LRU bound for URL deduplication
    MAX_CONCURRENCY = 10  # Max concurrent feed fetches

    def __init__(self):
        self.storage = StorageManager()
        self.kafka_publisher = KafkaPublisher()
        self.validator = Validator(kafka_publisher=self.kafka_publisher)
        self.kafka_publisher._validate = self.validator.validate_article
        self._seen_urls: OrderedDict[str, None] = OrderedDict()
        self.feed_state: Dict[str, Dict] = {}
        self.logger = logging.getLogger('rss_fetcher')
        self.last_activity = time.time()
        self.activity_log = {
            'successful_fetches': 0,
            'failed_fetches': 0,
            'last_success': None,
            'last_failure': None
        }

    def _make_client(self) -> httpx.AsyncClient:
        """Create a fresh httpx client scoped to the current event loop."""
        limits = httpx.Limits(
            max_keepalive_connections=50,
            max_connections=100,
            keepalive_expiry=30.0
        )
        return httpx.AsyncClient(
            limits=limits,
            timeout=httpx.Timeout(config.REQUEST_TIMEOUT),
            follow_redirects=True
        )

    async def fetch_feed(self, feed_url: str, feed_name: str) -> Optional[Dict]:
        """Fetch feed with async connection pooling and activity tracking."""
        headers = {
            **config.DEFAULT_HEADERS,
            'User-Agent': self._get_user_agent(),
            'If-None-Match': self.feed_state.get(feed_url, {}).get('etag', ''),
            'If-Modified-Since': self.feed_state.get(feed_url, {}).get('last_modified', '')
        }

        try:
            async with self._make_client() as client:
                await asyncio.sleep(config.RATE_LIMIT_DELAY)
                response = await client.get(feed_url, headers=headers)

                self.last_activity = time.time()

                if response.status_code == 304:
                    return None

                if response.status_code != 200:
                    self._log_activity(success=False, feed_name=feed_name)
                    return None

                self.feed_state[feed_url] = {
                    'etag': response.headers.get('ETag', ''),
                    'last_modified': response.headers.get('Last-Modified', '')
                }
                self._log_activity(success=True, feed_name=feed_name)

                return feedparser.parse(response.content)

        except Exception as e:
            self._log_activity(success=False, feed_name=feed_name, error=str(e))
            return None

    def _log_activity(self, success: bool, feed_name: str, error: str = None) -> None:
        """Track fetch activity and update metrics."""
        now = datetime.utcnow().isoformat()
        if success:
            self.activity_log['successful_fetches'] += 1
            self.activity_log['last_success'] = now
        else:
            self.activity_log['failed_fetches'] += 1
            self.activity_log['last_failure'] = now
            self.logger.warning(f"Fetch failed for {feed_name}: {error or 'Unknown error'}")

    def get_activity_metrics(self) -> Dict:
        """Return current activity metrics."""
        return {
            **self.activity_log,
            'seconds_since_last_activity': time.time() - self.last_activity,
        }

    async def process_feeds(self) -> List[Dict]:
        """Process all feeds concurrently with bounded concurrency."""
        feeds = FeedManager().load_feeds()
        semaphore = asyncio.Semaphore(self.MAX_CONCURRENCY)
        results = []

        async def process_one(feed: Dict) -> Optional[Dict]:
            async with semaphore:
                url = feed.get('url')
                name = feed.get('name')
                if not url or not name:
                    return None

                feed_data = await self.fetch_feed(url, name)
                if not feed_data or feed_data.bozo:
                    return None

                entries_count = self._process_feed_entries(feed_data.entries, name, url)
                return {'name': name, 'url': url, 'entries': entries_count}

        tasks = [process_one(feed) for feed in feeds]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        return [r for r in results if r is not None and not isinstance(r, Exception)]

    def _process_feed_entries(self, entries: List, feed_name: str, feed_url: str) -> int:
        """Process feed entries with duplicate checking. Returns count of new articles."""
        valid_articles = []
        for entry in entries:
            article_url = entry.get('link')
            if not article_url or self._is_duplicate(article_url):
                continue

            article = self._create_article_dict(entry, feed_name)
            if self.validator.validate_article(article):
                valid_articles.append(article)

        if valid_articles:
            self._save_and_publish_articles(valid_articles, feed_name, feed_url)

        return len(valid_articles)

    def _create_article_dict(self, entry: Dict, feed_name: str) -> Dict:
        """Create standardized article dictionary."""
        return {
            'title': entry.get('title', ''),
            'link': entry.get('link', ''),
            'published': entry.get('published', ''),
            'summary': entry.get('summary', entry.get('description', '')),
            'source': feed_name,
            'timestamp': datetime.utcnow().isoformat()
        }

    def _save_and_publish_articles(self, articles: List[Dict], feed_name: str, feed_url: str) -> None:
        """Handle storage and publishing."""
        self.storage.save_parsed_articles(articles, feed_name)
        self.storage.save_articles_to_master(articles)
        for article in articles:
            self.kafka_publisher.publish(config.KAFKA_TOPIC, article)

    def _is_duplicate(self, url: str) -> bool:
        """Check for duplicate URLs using hash with LRU eviction."""
        url_hash = hashlib.sha256(url.encode('utf-8')).hexdigest()
        if url_hash in self._seen_urls:
            self._seen_urls.move_to_end(url_hash)
            return True
        self._seen_urls[url_hash] = None
        if len(self._seen_urls) > self.MAX_SEEN_URLS:
            self._seen_urls.popitem(last=False)
        return False

    def _get_user_agent(self) -> str:
        """Rotate user agents."""
        return config.USER_AGENTS[len(self._seen_urls) % len(config.USER_AGENTS)]

    async def close(self) -> None:
        """Cleanup resources."""
        self.kafka_publisher.close()
