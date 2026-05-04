# rss_feeder/validator.py

import os
import json
import xml.etree.ElementTree as ET
import logging
from typing import List, Dict, Any, Optional
from rss_feeder import config

# Ensure failed_articles folder exists (ignore if no permission — Docker handles this)
try:
    os.makedirs(config.FAILED_ARTICLES_FOLDER, exist_ok=True)
    os.makedirs(os.path.dirname(config.INVALID_ARTICLES_LOG), exist_ok=True)
except PermissionError:
    pass

# Setup Logger for invalid articles
logger = logging.getLogger("invalid_articles_logger")
try:
    handler = logging.FileHandler(config.INVALID_ARTICLES_LOG)
    formatter = logging.Formatter('%(asctime)s - %(message)s')
    handler.setFormatter(formatter)
    logger.addHandler(handler)
except PermissionError:
    pass
logger.setLevel(logging.INFO)


class Validator:
    """Validates RSS feeds and articles."""

    dead_letter_topic = config.KAFKA_DEAD_LETTER_TOPIC
    failed_articles_counter: Dict[str, int] = {}

    def __init__(self, kafka_publisher: Optional[Any] = None):
        self.kafka_publisher = kafka_publisher

    @staticmethod
    def validate_feed_xml(xml_content: str) -> bool:
        """Validates if XML content is a valid RSS feed."""
        try:
            root = ET.fromstring(xml_content)
            return root.tag.lower() == "rss" or root.tag.lower().endswith("rss")
        except ET.ParseError:
            return False

    @staticmethod
    def validate_article(article: Dict[str, Any]) -> bool:
        """Checks if an article has required fields."""
        required_fields = ['title', 'link', 'published']
        return all(field in article and article[field] for field in required_fields)

    def filter_valid_articles(self, articles: List[Dict[str, Any]], feed_name: str = "UnknownFeed") -> List[Dict[str, Any]]:
        """Filters valid articles. Logs and saves invalid ones."""
        valid_articles = []
        invalid_articles = []

        for article in articles:
            if self.validate_article(article):
                valid_articles.append(article)
            else:
                invalid_articles.append(article)
                logger.info(f"Invalid article from {feed_name}: {article}")
                self.failed_articles_counter[feed_name] = self.failed_articles_counter.get(feed_name, 0) + 1

                # Send to dead-letter Kafka topic
                if config.SEND_TO_DEAD_LETTER_TOPIC and self.kafka_publisher is not None:
                    self.kafka_publisher.publish(self.dead_letter_topic, article)

        # Save invalid articles to JSON file
        if invalid_articles:
            self.save_failed_articles(invalid_articles, feed_name)

        return valid_articles

    @staticmethod
    def save_failed_articles(articles: List[Dict[str, Any]], feed_name: str) -> None:
        """Appends invalid articles into a failed_articles.json file."""
        failed_articles_file = os.path.join(config.FAILED_ARTICLES_FOLDER, "failed_articles.json")

        if os.path.exists(failed_articles_file):
            with open(failed_articles_file, 'r', encoding='utf-8') as f:
                existing_data = json.load(f)
        else:
            existing_data = {}

        existing_data.setdefault(feed_name, [])
        existing_data[feed_name].extend(articles)

        with open(failed_articles_file, 'w', encoding='utf-8') as f:
            json.dump(existing_data, f, indent=4)

    @classmethod
    def print_failure_summary(cls) -> None:
        """Prints the number of invalid articles per feed."""
        print("\nFailed articles per feed:")
        for feed, count in cls.failed_articles_counter.items():
            print(f"  - {feed}: {count} articles invalid")
