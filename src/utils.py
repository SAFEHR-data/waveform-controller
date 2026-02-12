import logging
import time


class DedupeFilter(logging.Filter):
    """Suppress repeated identical log messages within a time window."""

    def __init__(self, window_seconds=60, name=""):
        super().__init__(name)
        self.window_seconds = window_seconds
        self._last_message = None
        self._last_time = 0.0
        self._dedupe_count = 0

    def filter(self, record):
        msg = record.getMessage()
        now = time.monotonic()
        if msg == self._last_message and (now - self._last_time) < self.window_seconds:
            self._dedupe_count += 1
            return False
        self._last_message = msg
        self._last_time = now
        return True

