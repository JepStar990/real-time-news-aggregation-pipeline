# rss_feeder/storage_manager.py

import os
import json
from datetime import datetime
from typing import List, Dict, Any
from rss_feeder import config


class StorageManager:
    """Handles reading and writing files such as articles, raw feeds, and logs."""

    ARTICLES_FILE = os.path.join(config.ARTICLES_OUTPUT_DIR, "articles.jsonl")
    COMPACTION_SIZE_BYTES = 100 * 1024 * 1024  # 100 MB

    def __init__(self):
        for d in (config.RAW_FEEDS_DIR, config.PARSED_ARTICLES_DIR, config.LOGS_DIR,
                  config.ARTICLES_OUTPUT_DIR, config.XMLS_OUTPUT_DIR):
            try:
                os.makedirs(d, exist_ok=True)
            except PermissionError:
                pass

    def save_raw_feed(self, feed_content: str, feed_name: str) -> str:
        """Save the raw XML feed content."""
        filename = f"{feed_name}.xml"
        path = os.path.join(config.RAW_FEEDS_DIR, filename)
        with open(path, 'w', encoding=config.DEFAULT_ENCODING) as f:
            f.write(feed_content)
        return path

    def save_parsed_articles(self, articles: List[Dict[str, Any]], feed_name: str) -> str:
        """Save parsed articles to a file."""
        timestamp = datetime.utcnow().isoformat() if config.SAVE_WITH_TIMESTAMP else ""
        filename = f"{feed_name}_{timestamp}.json" if timestamp else f"{feed_name}.json"
        filename = filename.replace(":", "-")
        path = os.path.join(config.PARSED_ARTICLES_DIR, filename)
        with open(path, 'w', encoding=config.DEFAULT_ENCODING) as f:
            json.dump(articles, f, ensure_ascii=False, indent=2)
        return path

    def save_articles_to_master(self, new_articles: List[Dict[str, Any]]) -> None:
        """Append articles as JSONL lines. Compacts when file exceeds threshold."""
        with open(self.ARTICLES_FILE, 'a', encoding=config.DEFAULT_ENCODING) as f:
            for article in new_articles:
                f.write(json.dumps(article, ensure_ascii=False) + '\n')

        if os.path.getsize(self.ARTICLES_FILE) > self.COMPACTION_SIZE_BYTES:
            self._compact_articles()

    def _compact_articles(self) -> None:
        """Deduplicate articles by link and rewrite."""
        seen: set = set()
        deduped: list = []
        try:
            with open(self.ARTICLES_FILE, 'r', encoding=config.DEFAULT_ENCODING) as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        article = json.loads(line)
                    except json.JSONDecodeError:
                        continue
                    link = article.get('link')
                    if link and link not in seen:
                        seen.add(link)
                        deduped.append(article)

            with open(self.ARTICLES_FILE, 'w', encoding=config.DEFAULT_ENCODING) as f:
                for article in deduped:
                    f.write(json.dumps(article, ensure_ascii=False) + '\n')
        except FileNotFoundError:
            pass

    def read_all_articles(self) -> List[Dict[str, Any]]:
        """Read all articles from the JSONL file."""
        if not os.path.exists(self.ARTICLES_FILE):
            return []
        articles = []
        with open(self.ARTICLES_FILE, 'r', encoding=config.DEFAULT_ENCODING) as f:
            for line in f:
                line = line.strip()
                if line:
                    try:
                        articles.append(json.loads(line))
                    except json.JSONDecodeError:
                        continue
        return articles

    def save_log(self, message: str, filename: str = "default.log") -> None:
        """Save a log message."""
        path = os.path.join(config.LOGS_DIR, filename)
        timestamp = datetime.utcnow().isoformat()
        log_entry = f"[{timestamp}] {message}\n"
        with open(path, 'a', encoding=config.DEFAULT_ENCODING) as f:
            f.write(log_entry)
