import os
import json
from rss_feeder import config


def save_failed_articles(articles, feed_name):
    """Appends invalid articles into a failed_articles.json file."""
    failed_articles_file = os.path.join(
        config.FAILED_ARTICLES_FOLDER, "failed_articles.json"
    )

    if os.path.exists(failed_articles_file):
        with open(failed_articles_file, 'r', encoding='utf-8') as f:
            existing_data = json.load(f)
    else:
        existing_data = {}

    existing_data.setdefault(feed_name, [])
    existing_data[feed_name].extend(articles)

    with open(failed_articles_file, 'w', encoding='utf-8') as f:
        json.dump(existing_data, f, indent=4)
