@staticmethod
def validate_article(article):
    """Checks if an article has required fields."""
    required_fields = ['title', 'link', 'published']
    return all(field in article and article[field] for field in required_fields)
