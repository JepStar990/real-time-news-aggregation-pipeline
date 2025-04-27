import random
import time
import logging
import hashlib
from typing import Dict, Optional
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.jobstores.base import JobLookupError
from rss_feeder import config
from rss_feeder.rss_fetcher import RSSFetcher
from rss_feeder.feed_manager import FeedManager
from datetime import datetime

class FeedScheduler:
    """Adaptive feed scheduler with priority-based polling and batch processing"""

    def __init__(self):
        self.scheduler = BackgroundScheduler(
            job_defaults={
                'coalesce': True,
                'max_instances': 1,
                'misfire_grace_time': 60
            }
        )
        self.fetcher = RSSFetcher()
        self.feed_intervals: Dict[str, int] = {}
        self.feed_errors: Dict[str, int] = {}
        self.logger = logging.getLogger('feed_scheduler')
        self._load_feed_configs()

    def _load_feed_configs(self):
        """Initialize intervals from active feed configurations"""
        feeds = FeedManager().get_active_feeds()
        for feed in feeds:
            feed_name = feed.get('name')
            if feed_name:
                self.feed_intervals[feed_name] = feed.get('interval', config.DEFAULT_FEED_INTERVAL)
                self.feed_errors[feed_name] = feed.get('error_count', 0)

    def start(self):
        """Start scheduler with batched feed job registration"""
        self.logger.info("Initializing feed scheduler with batch processing")
        
        # Clear existing jobs safely
        try:
            self.scheduler.remove_all_jobs()
        except Exception as e:
            self.logger.warning("Error clearing existing jobs: %s", str(e))

        # Process feeds in batches
        feeds = FeedManager().get_active_feeds()
        batch_size = 50
        total_feeds = len(feeds)
        
        for i in range(0, total_feeds, batch_size):
            batch = feeds[i:i + batch_size]
            for feed in batch:
                self._add_feed_job(feed)
            time.sleep(0.1)  # Small delay between batches
            self.logger.debug("Registered batch %d-%d of %d", 
                            i + 1, min(i + batch_size, total_feeds), total_feeds)

        self.scheduler.start()
        self.logger.info("Scheduler started with %d active feed jobs", total_feeds)

    def _add_feed_job(self, feed: Dict):
        """Add a feed job with guaranteed unique ID and proper error handling"""
        feed_name = feed.get('name')
        feed_url = feed.get('url')
        priority = feed.get('priority', 'medium')
        
        if not feed_name or not feed_url:
            return
            
        # Generate unique job ID using name and URL hash
        url_hash = hashlib.md5(feed_url.encode()).hexdigest()[:8]
        job_id = f"{feed_name}_{url_hash}"
        
        # Remove existing job if present
        try:
            self.scheduler.remove_job(job_id)
        except JobLookupError:
            pass
            
        interval = self.feed_intervals.get(feed_name, config.DEFAULT_FEED_INTERVAL)
        trigger = IntervalTrigger(
            seconds=interval,
            jitter=config.JITTER_SECONDS
        )
        
        try:
            self.scheduler.add_job(
                self._poll_single_feed,
                args=[feed_name, feed_url],
                trigger=trigger,
                id=job_id,
                name=f"Poll {feed_name}",
                max_instances=1,
                misfire_grace_time=60,
                coalesce=True,
                priority=config.FEED_PRIORITIES.get(priority, 2)
            )
            self.logger.debug("Registered job for %s (interval: %ds)", feed_name, interval)
        except Exception as e:
            self.logger.error("Failed to register job for %s: %s", feed_name, str(e))

    def _poll_single_feed(self, feed_name: str, feed_url: str):
        """Poll an individual feed with comprehensive error handling"""
        start_time = time.time()
        try:
            self.logger.debug("Polling feed: %s", feed_name)
            
            feed_data = self.fetcher.fetch_feed(feed_url, feed_name)
            if feed_data and not feed_data.bozo:
                self._process_successful_poll(feed_name, feed_url, feed_data)
            else:
                self._process_failed_poll(feed_name, feed_url)
                
        except Exception as e:
            self.logger.error("Error polling %s: %s", feed_name, str(e))
            self._process_failed_poll(feed_name, feed_url)
        finally:
            elapsed = time.time() - start_time
            self.logger.debug("Completed polling %s in %.2fs", feed_name, elapsed)

    def _process_successful_poll(self, feed_name: str, feed_url: str, feed_data: Dict):
        """Handle successful feed poll with interval adjustment"""
        self.feed_errors[feed_name] = 0
        
        if feed_data.entries:
            processed = self.fetcher._process_feed_entries(feed_data.entries, feed_name, feed_url)
            if processed > 0:
                self._adjust_interval_based_on_activity(feed_name, feed_data)
                FeedManager().update_feed_status(feed_name, {
                    'last_success': datetime.utcnow().isoformat(),
                    'error_count': 0
                })

    def _process_failed_poll(self, feed_name: str, feed_url: str):
        """Handle failed poll with exponential backoff and status update"""
        self.feed_errors[feed_name] = self.feed_errors.get(feed_name, 0) + 1
        error_count = self.feed_errors[feed_name]
        
        backoff = min(
            config.DEFAULT_FEED_INTERVAL * (config.POLL_BACKOFF_FACTOR ** error_count),
            config.MAX_POLL_INTERVAL
        )
        backoff += random.uniform(0, config.JITTER_SECONDS)
        
        self._update_feed_interval(feed_name, backoff)
        FeedManager().update_feed_status(feed_name, {
            'last_error': datetime.utcnow().isoformat(),
            'error_count': error_count
        })
        
        self.logger.warning("Backoff %s to %.0fs (errors: %d)", 
                          feed_name, backoff, error_count)

    def _adjust_interval_based_on_activity(self, feed_name: str, feed_data: Dict):
        """Dynamically adjust polling interval based on feed activity"""
        current_interval = self.feed_intervals.get(feed_name, config.DEFAULT_FEED_INTERVAL)
        entry_count = len(feed_data.entries) if feed_data.entries else 0
        
        if entry_count > 20:  # High activity
            new_interval = max(current_interval * 0.8, config.MIN_POLL_INTERVAL)
        elif entry_count == 0:  # Low activity
            new_interval = min(current_interval * 1.2, config.MAX_POLL_INTERVAL)
        else:  # Moderate activity
            new_interval = current_interval

        # Apply server-suggested interval if available
        if 'updated_parsed' in feed_data.feed:
            server_interval = self._calculate_server_interval(feed_data)
            if server_interval:
                new_interval = max(server_interval, config.MIN_POLL_INTERVAL)

        if new_interval != current_interval:
            self._update_feed_interval(feed_name, new_interval)

    def _calculate_server_interval(self, feed_data: Dict) -> Optional[int]:
        """Determine suggested polling interval from server headers"""
        if 'updated_parsed' in feed_data.feed:
            last_update = time.mktime(feed_data.feed.updated_parsed)
            time_since_update = time.time() - last_update
            
            if time_since_update < 3600:  # Updated in last hour
                return config.MIN_POLL_INTERVAL
            elif time_since_update < 86400:  # Updated in last day
                return 1800  # 30 minutes
        return None

    def _update_feed_interval(self, feed_name: str, new_interval: int):
        """Update polling interval and reschedule job"""
        current_interval = self.feed_intervals.get(feed_name)
        if not current_interval or abs(current_interval - new_interval) > 60:
            self.feed_intervals[feed_name] = new_interval
            try:
                # Find job by name pattern
                jobs = [job for job in self.scheduler.get_jobs() 
                       if job.name == f"Poll {feed_name}"]
                if jobs:
                    jobs[0].reschedule(IntervalTrigger(
                        seconds=new_interval,
                        jitter=config.JITTER_SECONDS
                    ))
                    self.logger.info("Adjusted %s interval: %ds → %ds", 
                                   feed_name, current_interval, new_interval)
            except JobLookupError:
                self.logger.warning("Couldn't reschedule %s - job not found", feed_name)

    def shutdown(self):
        """Graceful shutdown procedure"""
        self.logger.info("Initiating scheduler shutdown...")
        try:
            self.fetcher.close()
            self.scheduler.shutdown(wait=True)
            self.logger.info("Scheduler shutdown complete")
        except Exception as e:
            self.logger.error("Shutdown error: %s", str(e))
            raise
