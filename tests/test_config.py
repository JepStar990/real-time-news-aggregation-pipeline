# tests/test_config.py

import unittest
from rss_feeder import config


class TestConfig(unittest.TestCase):
    def test_directories_exist_or_not(self):
        self.assertTrue(isinstance(config.DATA_DIR, str))
        self.assertTrue(isinstance(config.RAW_FEEDS_DIR, str))
        self.assertTrue(isinstance(config.PARSED_ARTICLES_DIR, str))
        self.assertTrue(isinstance(config.LOGS_DIR, str))
        self.assertTrue(isinstance(config.OUTPUTS_DIR, str))
        self.assertTrue(isinstance(config.ARTICLES_OUTPUT_DIR, str))
        self.assertTrue(isinstance(config.XMLS_OUTPUT_DIR, str))

    def test_default_headers(self):
        self.assertIn('User-Agent', config.DEFAULT_HEADERS)
        self.assertIn('Accept', config.DEFAULT_HEADERS)

    def test_kafka_config_present(self):
        self.assertTrue(isinstance(config.KAFKA_BROKER_URL, str))
        self.assertTrue(isinstance(config.KAFKA_TOPIC, str))
        self.assertTrue(isinstance(config.KAFKA_DEAD_LETTER_TOPIC, str))

    def test_user_agents_not_empty(self):
        self.assertTrue(len(config.USER_AGENTS) > 0)


if __name__ == "__main__":
    unittest.main()
