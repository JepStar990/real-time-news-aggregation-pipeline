from rss_feeder import config
from rss_feeder.kafka_publisher import KafkaPublisher


class DeadLetterPublisher:
    """Publishes invalid articles to Kafka dead-letter topic."""

    def __init__(self):
        self.topic = config.KAFKA_DEAD_LETTER_TOPIC
        self.publisher = KafkaPublisher()

    def publish(self, article):
        if not config.SEND_TO_DEAD_LETTER_TOPIC:
            return
        self.publisher.publish(self.topic, article)
