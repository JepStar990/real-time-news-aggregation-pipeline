from typing import Protocol, Dict, List, Any, Optional


class ArticleValidator(Protocol):
    """Protocol for article validation."""

    def validate_article(self, article: Dict[str, Any]) -> bool: ...

    def filter_valid_articles(self, articles: List[Dict[str, Any]], feed_name: str = "UnknownFeed") -> List[Dict[str, Any]]: ...


class MessagePublisher(Protocol):
    """Protocol for message publishing (e.g. Kafka)."""

    def publish(self, topic: str, message: Dict[str, Any]) -> bool: ...

    def flush(self) -> None: ...

    def close(self) -> None: ...
