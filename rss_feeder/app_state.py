# rss_feeder/app_state.py
"""Shared application state accessible from both __main__ and health modules."""

from typing import Optional

_current_application: Optional[object] = None


def get_application() -> Optional[object]:
    """Return the running Application instance, or None if not started."""
    return _current_application


def set_application(app: object) -> None:
    """Set the running Application instance."""
    global _current_application
    _current_application = app
