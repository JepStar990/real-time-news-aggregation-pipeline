# tests/test_kafka_publisher.py
import pytest
from unittest.mock import Mock, patch, MagicMock
from rss_feeder import config


def _always_valid(message):
    return True


def _always_invalid(message):
    return False


@pytest.fixture(autouse=True)
def mock_kafka_producer_class():
    """Patch KafkaProducer at the import location so no real connection is attempted."""
    with patch('rss_feeder.kafka_publisher.KafkaProducer', autospec=True) as mock:
        yield mock


@pytest.fixture
def kafka_publisher(mock_kafka_producer_class):
    from rss_feeder.kafka_publisher import KafkaPublisher
    return KafkaPublisher(validate_func=_always_valid)


def test_publish_success(kafka_publisher, mock_kafka_producer_class):
    test_message = {
        'title': 'Test Article',
        'link': 'http://example.com',
        'published': '2023-01-01'
    }

    mock_future = Mock()
    mock_kafka_producer_class.return_value.send.return_value = mock_future

    result = kafka_publisher.publish(config.KAFKA_TOPIC, test_message)
    assert result is True
    mock_kafka_producer_class.return_value.send.assert_called_once_with(
        config.KAFKA_TOPIC,
        value=test_message
    )


def test_publish_invalid_message(mock_kafka_producer_class):
    from rss_feeder.kafka_publisher import KafkaPublisher
    publisher = KafkaPublisher(validate_func=_always_invalid)
    invalid_message = {'title': 'Missing required fields'}

    result = publisher.publish(config.KAFKA_TOPIC, invalid_message)
    assert result is False


def test_publish_kafka_error(kafka_publisher, mock_kafka_producer_class):
    test_message = {
        'title': 'Test Article',
        'link': 'http://example.com',
        'published': '2023-01-01'
    }

    mock_kafka_producer_class.return_value.send.side_effect = Exception("Kafka error")

    result = kafka_publisher.publish(config.KAFKA_TOPIC, test_message)
    assert result is False


def test_flush_and_close(kafka_publisher, mock_kafka_producer_class):
    kafka_publisher.flush()
    mock_kafka_producer_class.return_value.flush.assert_called_once()

    kafka_publisher.close()
    mock_kafka_producer_class.return_value.close.assert_called_once()
