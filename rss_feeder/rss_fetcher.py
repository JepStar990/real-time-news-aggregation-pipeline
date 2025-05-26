# rss_feeder/rss_fetcher.py
import os
import time
import hashlib
import feedparser
import requests
from datetime import datetime
from typing import Dict, Optional, List
from rss_feeder import config
from rss_feeder.feed_manager import FeedManager
from rss_feeder.storage_manager import StorageManager
from rss_feeder.validator import Validator
from rss_feeder.kafka_publisher import KafkaPublisher

class RSSFetcher:
    """Fetch and process RSS feeds with connection pooling and activity tracking"""
    
    def __init__(self):
        self.storage = StorageManager()
        self.validator = Validator()
        self.kafka_publisher = KafkaPublisher()
        self.seen_urls = set()
        self.feed_state: Dict[str, Dict] = {}
        self._init_connection_pool()
        self.last_activity = time.time()
        self.activity_log = {
            'successful_fetches': 0,
            'failed_fetches': 0,
            'last_success': None,
            'last_failure': None
        }

    def _init_connection_pool(self):
        """Initialize HTTP connection pool"""
        self.session = requests.Session()
        adapter = requests.adapters.HTTPAdapter(
            pool_connections=100,
            pool_maxsize=100,
            max_retries=3,
            pool_block=False
        )
        self.session.mount('http://', adapter)
        self.session.mount('https://', adapter)

    def fetch_feed(self, feed_url: str, feed_name: str) -> Optional[Dict]:
        """Fetch feed with connection pooling and activity tracking"""
        headers = {
            **config.DEFAULT_HEADERS,
            'User-Agent': self._get_user_agent(),
            'If-None-Match': self.feed_state.get(feed_url, {}).get('etag', ''),
            'If-Modified-Since': self.feed_state.get(feed_url, {}).get('last_modified', '')
        }

        try:
            time.sleep(config.RATE_LIMIT_DELAY)
            response = self.session.get(
                feed_url,
                headers=headers,
                timeout=config.REQUEST_TIMEOUT
            )
            
            self.last_activity = time.time()
            
            if response.status_code == 304:
                return None
                
            if response.status_code != 200:
                self._log_activity(success=False, feed_name=feed_name)
                return None

            # Update state and log success
            self.feed_state[feed_url] = {
                'etag': response.headers.get('ETag', ''),
                'last_modified': response.headers.get('Last-Modified', '')
            }
            self._log_activity(success=True, feed_name=feed_name)
            
            return feedparser.parse(response.content)

        except Exception as e:
            self._log_activity(success=False, feed_name=feed_name, error=str(e))
            return None

    def _log_activity(self, success: bool, feed_name: str, error: str = None):
        """Track fetch activity and update metrics"""
        now = datetime.utcnow().isoformat()
        if success:
            self.activity_log['successful_fetches'] += 1
            self.activity_log['last_success'] = now
        else:
            self.activity_log['failed_fetches'] += 1
            self.activity_log['last_failure'] = now
            logging.warning(f"Fetch failed for {feed_name}: {error or 'Unknown error'}")

    def get_activity_metrics(self) -> Dict:
        """Return current activity metrics"""
        return {
            **self.activity_log,
            'seconds_since_last_activity': time.time() - self.last_activity,
            'active_connections': len(self.session.adapters.values())
        }

    def process_feeds(self):
        """Process all feeds with activity monitoring"""
        feeds = FeedManager().load_feeds()
        for feed in feeds:
            url = feed.get('url')
            name = feed.get('name')
            if not url or not name:
                continue

            feed_data = self.fetch_feed(url, name)
            if not feed_data or feed_data.bozo:
                continue

            self._process_feed_entries(feed_data.entries, name, url)

    def _process_feed_entries(self, entries: List, feed_name: str, feed_url: str):
        """Process feed entries with duplicate checking"""
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

    def _create_article_dict(self, entry: Dict, feed_name: str) -> Dict:
        """Create standardized article dictionary"""
        return {
            'title': entry.get('title', ''),
            'link': entry.get('link', ''),
            'published': entry.get('published', ''),
            'summary': entry.get('summary', entry.get('description', '')),
            'source': feed_name,
            'timestamp': datetime.utcnow().isoformat()
        }

    def _save_and_publish_articles(self, articles: List[Dict], feed_name: str, feed_url: str):
        """Handle storage and publishing"""
        self.storage.save_parsed_articles(articles, feed_name)
        self.storage.save_articles_to_master(articles)
        for article in articles:
            self.kafka_publisher.publish(config.KAFKA_TOPIC, article)

    def _is_duplicate(self, url: str) -> bool:
        """Check for duplicate URLs using hash"""
        url_hash = hashlib.sha256(url.encode('utf-8')).hexdigest()
        if url_hash in self.seen_urls:
            return True
        self.seen_urls.add(url_hash)
        return False

    def _get_user_agent(self) -> str:
        """Rotate user agents"""
        return config.USER_AGENTS[len(self.seen_urls) % len(config.USER_AGENTS)]

    def close(self):
        """Cleanup resources"""
        self.session.close()
        self.kafka_publisher.close()
