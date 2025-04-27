# rss_feeder/storage_manager.py

import os
import json
from datetime import datetime
from rss_feeder import config

class StorageManager:
    """Handles reading and writing files such as articles, raw feeds, and logs."""

    def __init__(self):
        # Ensure required directories exist
        os.makedirs(config.RAW_FEEDS_DIR, exist_ok=True)
        os.makedirs(config.PARSED_ARTICLES_DIR, exist_ok=True)
        os.makedirs(config.LOGS_DIR, exist_ok=True)
        os.makedirs(config.ARTICLES_OUTPUT_DIR, exist_ok=True)
        os.makedirs(config.XMLS_OUTPUT_DIR, exist_ok=True)
        # Ensure required directories exist
        os.makedirs(config.RAW_FEEDS_DIR, exist_ok=True)
        os.makedirs(config.PARSED_ARTICLES_DIR, exist_ok=True)
        os.makedirs(config.LOGS_DIR, exist_ok=True)
        # Only create these if they're defined in config
        if hasattr(config, 'ARTICLES_OUTPUT_DIR'):
            os.makedirs(config.ARTICLES_OUTPUT_DIR, exist_ok=True)
        if hasattr(config, 'XMLS_OUTPUT_DIR'):
            os.makedirs(config.XMLS_OUTPUT_DIR, exist_ok=True)

    def save_raw_feed(self, feed_content, feed_name):
        """Save the raw XML feed content."""
        filename = f"{feed_name}.xml"
        path = os.path.join(config.RAW_FEEDS_DIR, filename)
        with open(path, 'w', encoding=config.DEFAULT_ENCODING) as f:
            f.write(feed_content)
        return path

    def save_parsed_articles(self, articles, feed_name):
        """Save parsed articles to a file."""
        timestamp = datetime.utcnow().isoformat() if config.SAVE_WITH_TIMESTAMP else ""
        filename = f"{feed_name}_{timestamp}.json" if timestamp else f"{feed_name}.json"
        filename = filename.replace(":", "-")  # Safe for Windows
        path = os.path.join(config.PARSED_ARTICLES_DIR, filename)
        with open(path, 'w', encoding=config.DEFAULT_ENCODING) as f:
            json.dump(articles, f, ensure_ascii=False, indent=2)
        return path

    def save_articles_to_master(self, new_articles):
        """Append new articles to the master articles.json file."""
        articles = []
        if os.path.exists(config.ARTICLES_JSON_FILE):
            with open(config.ARTICLES_JSON_FILE, 'r', encoding=config.DEFAULT_ENCODING) as f:
                try:
                    articles = json.load(f)
                except json.JSONDecodeError:
                    articles = []
        
        articles.extend(new_articles)
        
        with open(config.ARTICLES_JSON_FILE, 'w', encoding=config.DEFAULT_ENCODING) as f:
            json.dump(articles, f, ensure_ascii=False, indent=2)
    
    def save_log(self, message, filename="default.log"):
        """Save a log message."""
        path = os.path.join(config.LOGS_DIR, filename)
        timestamp = datetime.utcnow().isoformat()
        log_entry = f"[{timestamp}] {message}\n"
        with open(path, 'a', encoding=config.DEFAULT_ENCODING) as f:
            f.write(log_entry)


