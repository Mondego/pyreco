"""Relevant result:addHandler"""
import logging
try:  # Python 2.7+
    from logging import NullHandler
except ImportError:
    class NullHandler(logging.Handler):
        def emit(self, record):
            pass
logger = logging.getLogger(__name__)
logger.
