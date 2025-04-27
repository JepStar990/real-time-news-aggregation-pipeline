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
    """Fetch and process RSS feeds with proper headers, rate limiting, and modular components"""
    
    def __init__(self):
        self.storage = StorageManager()
        self.validator = Validator()
        self.kafka_publisher = KafkaPublisher()
        self.seen_urls = set()
        self.feed_state: Dict[str, Dict] = {}  # Stores ETag/Last-Modified per feed
        
    def fetch_feed(self, feed_url: str, feed_name: str) -> Optional[Dict]:
        """Fetch feed with proper headers and rate limiting"""
        headers = {
            **config.DEFAULT_HEADERS,
            'User-Agent': self._get_user_agent(),
            'If-None-Match': self.feed_state.get(feed_url, {}).get('etag', ''),
            'If-Modified-Since': self.feed_state.get(feed_url, {}).get('last_modified', '')
        }
        
        try:
            # Rate limiting
            time.sleep(config.RATE_LIMIT_DELAY)
            
            response = requests.get(
                feed_url,
                headers=headers,
                timeout=config.REQUEST_TIMEOUT
            )
            
            if response.status_code == 304:
                print(f"Feed {feed_name} not modified since last fetch")
                return None
                
            if response.status_code != 200:
                print(f"Failed to fetch {feed_name}: HTTP {response.status_code}")
                return None
                
            # Update feed state with new headers
            self.feed_state[feed_url] = {
                'etag': response.headers.get('ETag', ''),
                'last_modified': response.headers.get('Last-Modified', '')
            }
            
            return feedparser.parse(response.content)
            
        except Exception as e:
            print(f"Error fetching {feed_name}: {str(e)}")
            return None
    
    def process_feeds(self):
        """Process all feeds from FeedManager"""
        feeds = FeedManager().load_feeds()
        
        for feed in feeds:
            url = feed.get('url')
            name = feed.get('name')
            if not url or not name:
                continue
                
            print(f"Processing feed: {name}")
            feed_data = self.fetch_feed(url, name)
            if not feed_data or feed_data.bozo:
                continue
                
            self._process_feed_entries(feed_data.entries, name, url)
    
    def _process_feed_entries(self, entries: List, feed_name: str, feed_url: str):
        """Process individual feed entries"""
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
        """Handle storage and publishing of valid articles"""
        # Save to storage
        self.storage.save_parsed_articles(articles, feed_name)
        self.storage.save_articles_to_master(articles)
        
        # Publish to Kafka
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
        """Rotate user agents from config to avoid being blocked"""
        return config.USER_AGENTS[len(self.seen_urls) % len(config.USER_AGENTS)]
    
    def close(self):
        """Cleanup resources"""
        self.kafka_publisher.close()
