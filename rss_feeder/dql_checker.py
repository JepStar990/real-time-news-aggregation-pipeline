import re
from datetime import datetime

class DQLChecker:
    """Simple Data Quality Layer checker for articles"""

    TITLE_MIN_LENGTH = 10
    URL_REGEX = re.compile(r'https?://\S+')

    @staticmethod
    def is_valid_title(title):
        return bool(title) and len(title.strip()) >= DQLChecker.TITLE_MIN_LENGTH

    @staticmethod
    def is_valid_link(link):
        return bool(link) and DQLChecker.URL_REGEX.match(link)

    @staticmethod
    def is_valid_published(published):
        if not published:
            return False
        try:
            datetime.strptime(published, "%a, %d %b %Y %H:%M:%S %z")
            return True
        except Exception:
            return False

    @classmethod
    def validate_article(cls, article):
        """Simple True/False validation"""
        return (
            cls.is_valid_title(article.get('title')) and
            cls.is_valid_link(article.get('link')) and
            cls.is_valid_published(article.get('published'))
        )

    @classmethod
    def validate_article_with_reason(cls, article):
        """Validation + reason why it failed"""
        if not cls.is_valid_title(article.get('title')):
            return False, "Title is too short or missing"
        if not cls.is_valid_link(article.get('link')):
            return False, "Invalid or missing URL"
        if not cls.is_valid_published(article.get('published')):
            return False, "Missing or invalid published date"
        return True, ""

