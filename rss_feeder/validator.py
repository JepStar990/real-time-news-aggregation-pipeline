# rss_feeder/validator.py

import os
import json
import xml.etree.ElementTree as ET
import logging
from rss_feeder import config
from rss_feeder.domain.rules import validate_article
from rss_feeder.adapters.storage.file_failure_store import save_failed_articles
from rss_feeder.adapters.messaging.dead_letter_publisher import DeadLetterPublisher

# Setup Logger for invalid articles
logger = logging.getLogger("invalid_articles_logger")
handler = logging.FileHandler(config.INVALID_ARTICLES_LOG)
formatter = logging.Formatter('%(asctime)s - %(message)s')
handler.setFormatter(formatter)
logger.addHandler(handler)
logger.setLevel(logging.INFO)

# Ensure failed_articles folder exists
os.makedirs(config.FAILED_ARTICLES_FOLDER, exist_ok=True)

class Validator:
    """Validates RSS feeds and articles."""

    dead_letter_publisher = DeadLetterPublisher()
    failed_articles_counter = {}

    @staticmethod
    def validate_feed_xml(xml_content):
        """Validates if XML content is a valid RSS feed."""
        try:
            root = ET.fromstring(xml_content)
            return root.tag.lower() == "rss" or root.tag.lower().endswith("rss")
        except ET.ParseError:
            return False

    @staticmethod
    def validate_article(article):
        """Checks if an article has required fields."""
        required_fields = ['title', 'link', 'published']
        return all(field in article and article[field] for field in required_fields)

    @classmethod
    def filter_valid_articles(cls, articles, feed_name="UnknownFeed"):
        """Filters valid articles. Logs and saves invalid ones."""
        valid_articles = []
        invalid_articles = []

        for article in articles:
            if validate_article(article):
                valid_articles.append(article)
            else:
                invalid_articles.append(article)
                logger.info(f"Invalid article from {feed_name}: {article}")
                cls.failed_articles_counter[feed_name] = cls.failed_articles_counter.get(feed_name, 0) + 1

                # Send to dead-letter Kafka topic (lazily initialize publisher)
                cls.dead_letter_publisher.publish(article)

        # Save invalid articles to JSON file
        if invalid_articles:
            save_failed_articles(invalid_articles, feed_name)

        return valid_articles

    @classmethod
    def print_failure_summary(cls):
        """Prints the number of invalid articles per feed."""
        print("\nFailed articles per feed:")
        for feed, count in cls.failed_articles_counter.items():
            print(f"  - {feed}: {count} articles invalid")

