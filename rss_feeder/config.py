# config.py

import os
from datetime import timedelta

# ========== Kafka Config ==========
KAFKA_BROKER_URL = "localhost:9092"
KAFKA_TOPIC = "rss_articles"

# ========== Storage Paths ==========
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "..", "data")
RAW_FEEDS_DIR = os.path.join(DATA_DIR, "raw_feeds")
PARSED_ARTICLES_DIR = os.path.join(DATA_DIR, "parsed_articles")
LOGS_DIR = os.path.join(DATA_DIR, "logs")
OUTPUTS_DIR = os.path.join(BASE_DIR, "..", "outputs")
ARTICLES_FILE = os.path.join(OUTPUTS_DIR, "articles", "articles.json")
ARTICLES_OUTPUT_DIR = os.path.join(OUTPUTS_DIR, "articles")
XMLS_OUTPUT_DIR = os.path.join(OUTPUTS_DIR, "xmls")
ARTICLES_JSON_FILE = os.path.join(ARTICLES_OUTPUT_DIR, "articles.json")
DEFAULT_ENCODING = 'utf-8'

# ========== Fetcher/Request Settings ==========
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"

DEFAULT_HEADERS = {
    "User-Agent": USER_AGENT,
    "Accept": "application/rss+xml, application/xml;q=0.9, */*;q=0.8"
}
REQUEST_TIMEOUT = 10  # seconds
RATE_LIMIT_DELAY = 1  # seconds between requests

# ========== Scheduler Settings ==========
SCHEDULER_INTERVAL_SECONDS = 300  # poll every 5 minutes

# ========== Miscellaneous ==========
SAVE_WITH_TIMESTAMP = True  # articles.json will include timestamps

# ========== Validator Settings ==========
FAILED_ARTICLES_FOLDER = os.getenv("FAILED_ARTICLES_FOLDER", "data/failed_articles")
INVALID_ARTICLES_LOG = os.getenv("INVALID_ARTICLES_LOG", "data/logs/invalid_articles.log")
KAFKA_DEAD_LETTER_TOPIC = os.getenv("KAFKA_DEAD_LETTER_TOPIC", "dead_letter_articles")
SEND_TO_DEAD_LETTER_TOPIC = os.getenv("SEND_TO_DEAD_LETTER_TOPIC", "true").lower() == "true"

# ========== User Agents ==========
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
    "Mozilla/5.0 (macOS; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.1.1 Safari/605.1.15",
    "Mozilla/5.0 (Linux; Android 11; Pixel 5) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.77 Mobile Safari/537.36",
    "Mozilla/5.0 (iPhone; CPU iPhone OS 14_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.0 Mobile/15E148 Safari/604.1",
    "Mozilla/5.0 (Linux; Android 10; SM-G973F) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.77 Mobile Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Gecko/20100101 Firefox/89.0",
    "Mozilla/5.0 (Windows NT 6.1; WOW64; rv:89.0) Gecko/20100101 Firefox/89.0",
    "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:89.0) Gecko/20100101 Firefox/89.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/90.0.4430.93 Safari/537.36",
    "Mozilla/5.0 (compatible; Googlebot/2.1; +http://www.google.com/bot.html)",
    "Mozilla/5.0 (compatible; Bingbot/2.0; +http://www.bing.com/bingbot.htm)"
]
# Update DEFAULT_HEADERS to use the first user agent
DEFAULT_HEADERS = {
    "Accept": "application/rss+xml, application/xml;q=0.9, */*;q=0.8"
}


# ========== Scheduler Settings ==========
MIN_POLL_INTERVAL = 300  # 5 minutes (absolute minimum)
MAX_POLL_INTERVAL = 86400  # 24 hours (for inactive feeds)
POLL_BACKOFF_FACTOR = 2  # Multiplier for error backoff
DEFAULT_FEED_INTERVAL = 3600  # 1 hour (default for new feeds)
JITTER_SECONDS = 30  # Randomness to avoid synchronized requests
FEED_PRIORITIES = {
    'high': 1,
    'medium': 2,
    'low': 3
}

