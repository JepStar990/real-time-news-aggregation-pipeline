# tests/test_validator.py

import os
import json
import shutil
import pytest
from unittest.mock import MagicMock, patch
from rss_feeder.validator import Validator
from rss_feeder import config

# Test data
valid_article = {
    "title": "Test Title",
    "link": "http://example.com/article",
    "published": "2024-04-27"
}

invalid_article = {
    "title": "",
    "link": "",
    # 'published' is missing
}

@pytest.fixture(autouse=True)
def cleanup_failed_articles_folder():
    """Clean up failed_articles folder before each test."""
    if os.path.exists(config.FAILED_ARTICLES_FOLDER):
        shutil.rmtree(config.FAILED_ARTICLES_FOLDER)
    os.makedirs(config.FAILED_ARTICLES_FOLDER, exist_ok=True)
    # Reset kafka publisher and counter for isolated tests
    Validator.kafka_publisher = None
    Validator.failed_articles_counter = {}

def test_validate_feed_xml_valid():
    xml = "<rss><channel><title>Test Feed</title></channel></rss>"
    assert Validator.validate_feed_xml(xml) == True

def test_validate_feed_xml_invalid():
    xml = "<html><body>Not RSS</body></html>"
    assert Validator.validate_feed_xml(xml) == False

def test_validate_article_valid():
    assert Validator.validate_article(valid_article) == True

def test_validate_article_invalid():
    assert Validator.validate_article(invalid_article) == False

@patch('rss_feeder.validator.KafkaPublisher')
def test_filter_valid_articles_separates_good_and_bad(mock_kafka):
    mock_instance = MagicMock()
    mock_kafka.return_value = mock_instance

    articles = [valid_article, invalid_article]
    feed_name = "TestFeed"

    valid = Validator.filter_valid_articles(articles, feed_name=feed_name)

    assert valid == [valid_article]

    failed_json_path = os.path.join(config.FAILED_ARTICLES_FOLDER, "failed_articles.json")
    assert os.path.exists(failed_json_path)

    with open(failed_json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
        assert feed_name in data
        assert invalid_article in data[feed_name]

    # Kafka publisher should've been called once
    mock_instance.publish.assert_called_once()

@patch('rss_feeder.validator.KafkaPublisher')
def test_failed_articles_counter(mock_kafka):
    mock_instance = MagicMock()
    mock_kafka.return_value = mock_instance

    articles = [invalid_article, invalid_article]
    feed_name = "CounterFeed"

    Validator.filter_valid_articles(articles, feed_name=feed_name)

    assert Validator.failed_articles_counter.get(feed_name) == 2
    assert mock_instance.publish.call_count == 2

