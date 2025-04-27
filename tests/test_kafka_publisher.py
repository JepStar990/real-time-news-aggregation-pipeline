# tests/test_kafka_publisher.py
import pytest
from unittest.mock import Mock, patch
from rss_feeder.kafka_publisher import KafkaPublisher
from rss_feeder import config

@pytest.fixture
def mock_producer():
    with patch('kafka.KafkaProducer') as mock:
        yield mock

@pytest.fixture
def kafka_publisher(mock_producer):
    return KafkaPublisher()

def test_publish_success(kafka_publisher, mock_producer):
    """Test successful message publication"""
    test_message = {
        'title': 'Test Article',
        'link': 'http://example.com',
        'published': '2023-01-01'
    }
    
    # Mock the future object
    mock_future = Mock()
    mock_producer.return_value.send.return_value = mock_future
    
    result = kafka_publisher.publish(config.KAFKA_TOPIC, test_message)
    assert result is True
    mock_producer.return_value.send.assert_called_once_with(
        config.KAFKA_TOPIC, 
        value=test_message
    )

def test_publish_invalid_message(kafka_publisher, mock_producer):
    """Test publication with invalid message structure"""
    invalid_message = {'title': 'Missing required fields'}
    
    result = kafka_publisher.publish(config.KAFKA_TOPIC, invalid_message)
    assert result is False
    
    # Should not call send on main topic
    mock_producer.return_value.send.assert_not_called()
    
    # Should send to dead letter topic if configured
    if config.SEND_TO_DEAD_LETTER_TOPIC:
        mock_producer.return_value.send.assert_called_once_with(
            config.KAFKA_DEAD_LETTER_TOPIC,
            value={
                'original_message': invalid_message,
                'error_reason': 'Invalid article structure',
                'timestamp': pytest.approx(invalid_message.get('timestamp'))
            }
        )

def test_publish_kafka_error(kafka_publisher, mock_producer):
    """Test handling of Kafka errors"""
    test_message = {
        'title': 'Test Article',
        'link': 'http://example.com',
        'published': '2023-01-01'
    }
    
    # Simulate Kafka error
    mock_producer.return_value.send.side_effect = Exception("Kafka error")
    
    result = kafka_publisher.publish(config.KAFKA_TOPIC, test_message)
    assert result is False
    
    if config.SEND_TO_DEAD_LETTER_TOPIC:
        mock_producer.return_value.send.assert_called_with(
            config.KAFKA_DEAD_LETTER_TOPIC,
            value={
                'original_message': test_message,
                'error_reason': 'Kafka error',
                'timestamp': pytest.approx(test_message.get('timestamp'))
            }
        )

def test_flush_and_close(kafka_publisher, mock_producer):
    """Test flush and close methods"""
    kafka_publisher.flush()
    mock_producer.return_value.flush.assert_called_once()
    
    kafka_publisher.close()
    mock_producer.return_value.close.assert_called_once()

def test_dead_letter_topic_handling(kafka_publisher, mock_producer):
    """Test that invalid messages go to dead letter topic"""
    # Temporarily enable dead letter topic
    original_setting = config.SEND_TO_DEAD_LETTER_TOPIC
    config.SEND_TO_DEAD_LETTER_TOPIC = True
    
    invalid_message = {'title': 'Missing required fields'}
    kafka_publisher.publish(config.KAFKA_TOPIC, invalid_message)
    
    mock_producer.return_value.send.assert_called_once_with(
        config.KAFKA_DEAD_LETTER_TOPIC,
        value={
            'original_message': invalid_message,
            'error_reason': 'Invalid article structure',
            'timestamp': pytest.approx(invalid_message.get('timestamp'))
        }
    )
    
    # Restore original setting
    config.SEND_TO_DEAD_LETTER_TOPIC = original_setting
