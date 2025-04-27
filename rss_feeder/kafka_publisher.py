# rss_feeder/kafka_publisher.py
import json
import logging
from kafka import KafkaProducer
from kafka.errors import KafkaError
from rss_feeder import config

class KafkaPublisher:
    """Handles publishing messages to Kafka topics with DQL handling"""
    
    def __init__(self):
        self.producer = KafkaProducer(
            bootstrap_servers=[config.KAFKA_BROKER_URL],
            value_serializer=lambda v: json.dumps(v).encode('utf-8'),
            retries=3,
            max_in_flight_requests_per_connection=1
        )
        self.logger = logging.getLogger('kafka_publisher')
        
    def publish(self, topic, message):
        """Publish message to Kafka topic with error handling"""
        try:
            # Delay the import here to avoid circular dependency
            from rss_feeder.validator import Validator

            # Validate message before sending
            if not Validator.validate_article(message):
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
    
    def _on_send_success(self, topic, record_metadata):
        self.logger.debug(f"Successfully published to {topic} partition {record_metadata.partition}")
    
    def _on_send_error(self, topic, message, exc):
        self.logger.error(f"Failed to publish to {topic}: {exc}")
        self._handle_invalid_message(message, str(exc))
    
    def _handle_invalid_message(self, message, reason):
        """Handle messages that failed validation or publishing"""
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
    
    def flush(self):
        """Flush any pending messages"""
        self.producer.flush()
    
    def close(self):
        """Cleanup producer"""
        self.producer.close()
