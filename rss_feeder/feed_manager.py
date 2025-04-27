# rss_feeder/feed_manager.py
import json
import logging
import os
from typing import List, Dict
from datetime import datetime
from rss_feeder import config

class FeedManager:
    """Manage RSS feed configurations with validation and deduplication"""

    def __init__(self, feeds_file: str = None):
        self.feeds_file = feeds_file or os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            'feeds.json'
        )
        self.logger = logging.getLogger('feed_manager')
        self.last_modified = 0
        self.cached_feeds = None

    def load_feeds(self) -> List[Dict]:
        """Load and validate feeds from JSON file with caching and deduplication"""
        try:
            # Check file modification time for cache invalidation
            file_mtime = os.path.getmtime(self.feeds_file)
            if self.cached_feeds and file_mtime <= self.last_modified:
                return self.cached_feeds

            with open(self.feeds_file, 'r', encoding='utf-8') as f:
                feeds = json.load(f)

            validated_feeds = []
            seen = set()  # Track (name, url) pairs for deduplication

            for feed in feeds:
                if self._validate_feed(feed):
                    feed_id = (feed['name'], feed['url'])
                    if feed_id not in seen:
                        seen.add(feed_id)
                        validated_feeds.append(self._apply_defaults(feed))

            self.cached_feeds = validated_feeds
            self.last_modified = file_mtime
            return validated_feeds

        except json.JSONDecodeError as e:
            self.logger.error("Invalid JSON in feeds file: %s", str(e))
            return []
        except Exception as e:
            self.logger.error("Error loading feeds: %s", str(e))
            return []

    def _validate_feed(self, feed: Dict) -> bool:
        """Validate required feed fields and structure"""
        if not isinstance(feed, dict):
            self.logger.warning("Invalid feed entry (not a dict): %s", feed)
            return False

        required_fields = ['name', 'url']
        for field in required_fields:
            if not feed.get(field):
                self.logger.warning("Missing required field '%s' in feed: %s", field, feed)
                return False

        if not isinstance(feed['name'], str) or not isinstance(feed['url'], str):
            self.logger.warning("Invalid name/url type in feed: %s", feed)
            return False

        return True

    def _apply_defaults(self, feed: Dict) -> Dict:
        """Apply default values to feed configuration"""
        return {
            'name': feed['name'],
            'url': feed['url'],
            'interval': feed.get('interval', config.DEFAULT_FEED_INTERVAL),
            'priority': feed.get('priority', 'medium'),
            'last_updated': feed.get('last_updated'),
            'error_count': feed.get('error_count', 0),
            'active': feed.get('active', True)
        }

    def update_feed_status(self, feed_name: str, status: Dict):
        """Update feed status in the configuration file"""
        try:
            with open(self.feeds_file, 'r+', encoding='utf-8') as f:
                feeds = json.load(f)
                for feed in feeds:
                    if feed['name'] == feed_name:
                        feed.update(status)
                        feed['last_updated'] = datetime.utcnow().isoformat()
                        break

                f.seek(0)
                json.dump(feeds, f, indent=2)
                f.truncate()

            # Invalidate cache
            self.cached_feeds = None
        except Exception as e:
            self.logger.error("Error updating feed status: %s", str(e))

    def get_active_feeds(self) -> List[Dict]:
        """Return only active feeds"""
        return [feed for feed in self.load_feeds() if feed.get('active', True)]
