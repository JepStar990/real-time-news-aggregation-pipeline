# tests/test_config.py

import unittest
import os
from rss_feeder import config

class TestConfig(unittest.TestCase):
    def test_directories_exist_or_not(self):
        # Check that all important directories are correctly set as paths
        self.assertTrue(isinstance(config.DATA_DIR, str))
        self.assertTrue(isinstance(config.RAW_FEEDS_DIR, str))
        self.assertTrue(isinstance(config.PARSED_ARTICLES_DIR, str))
        self.assertTrue(isinstance(config.LOGS_DIR, str))
        self.assertTrue(isinstance(config.OUTPUTS_DIR, str))
        self.assertTrue(isinstance(config.ARTICLES_OUTPUT_DIR, str))
        self.assertTrue(isinstance(config.XMLS_OUTPUT_DIR, str))

    def test_articles_json_file_path(self):
        # Ensure the articles.json points to a .json file
        self.assertTrue(config.ARTICLES_JSON_FILE.endswith('.json'))

    def test_default_headers(self):
        # Check User-Agent header exists
        self.assertIn('User-Agent', config.DEFAULT_HEADERS)
        self.assertTrue(config.DEFAULT_HEADERS['User-Agent'].startswith("AI-News-RadioBot"))

if __name__ == "__main__":
    unittest.main()

