Validator
=========

Handles article-level validation rules.

Responsibilities
----------------
- Ensure required article fields exist
- Reject malformed or empty articles
- Enforce basic data quality rules

Current Location
----------------
rss_feeder/validator.py

Future Location
---------------
rss_feeder/domain/rules.py

Extracted Domain Logic
---------------------
The ``validate_article`` rule has been moved to:

``rss_feeder.domain.rules``

This is the first step in decomposing the validator module.

Extracted Storage Logic
----------------------
Persistence of invalid articles has been moved to a storage adapter:

``rss_feeder.adapters.storage.file_failure_store``

This adapter is responsible for filesystem interactions and JSON persistence.
