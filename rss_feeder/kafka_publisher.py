# rss_feeder/kafka_publisher.py
import json
import logging
from datetime import datetime
from typing import Callable, Dict, Any, Optional
from kafka import KafkaProducer
from kafka.errors import KafkaError
from rss_feeder import config


def _default_validate(message: Dict[str, Any]) -> bool:
    """Default no-op validator — accepts all messages."""
    return True


class KafkaPublisher:
    """Handles publishing messages to Kafka topics with DQL handling."""

    def __init__(self, validate_func: Optional[Callable[[Dict[str, Any]], bool]] = None):
        self._validate = validate_func or _default_validate
        self.producer = KafkaProducer(
            bootstrap_servers=[config.KAFKA_BROKER_URL],
            value_serializer=lambda v: json.dumps(v).encode('utf-8'),
            retries=3,
            max_in_flight_requests_per_connection=1
        )
        self.logger = logging.getLogger('kafka_publisher')

    def publish(self, topic: str, message: Dict[str, Any]) -> bool:
        """Publish message to Kafka topic with error handling."""
        try:
            if not self._validate(message):
                self._handle_invalid_message(message, "Invalid article structure")
                return False

            future = self.producer.send(topic, value=message)
            future.add_callback(self._on_send_success, topic)
            future.add_errback(self._on_send_error, topic, message)
            return True
        except Exception as e:
            self.logger.error(f"Failed to publish to {topic}: {str(e)}")
            self._handle_invalid_message(message, str(e))
            return False

    def _on_send_success(self, topic: str, record_metadata) -> None:
        self.logger.debug(f"Successfully published to {topic} partition {record_metadata.partition}")

    def _on_send_error(self, topic: str, message: Dict[str, Any], exc: Exception) -> None:
        self.logger.error(f"Failed to publish to {topic}: {exc}")
        self._handle_invalid_message(message, str(exc))

    def _handle_invalid_message(self, message: Dict[str, Any], reason: str) -> None:
        """Handle messages that failed validation or publishing."""
        if config.SEND_TO_DEAD_LETTER_TOPIC:
            try:
                error_message = {
                    'original_message': message,
                    'error_reason': reason,
                    'timestamp': datetime.utcnow().isoformat()
                }
                self.producer.send(config.KAFKA_DEAD_LETTER_TOPIC, value=error_message)
            except Exception as e:
                self.logger.error(f"Failed to send to dead letter topic: {str(e)}")

    def flush(self) -> None:
        """Flush any pending messages."""
        self.producer.flush()

    def close(self) -> None:
        """Cleanup producer."""
        self.producer.close()
