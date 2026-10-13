"""Coalesce rapid slider changes: send only the latest value, at most once per interval."""

from collections.abc import Hashable


class Coalescer:
    def __init__(self, interval_s: float = 0.2) -> None:
        self._interval = interval_s
        self._pending: dict[Hashable, int] = {}
        self._last_sent: dict[Hashable, float] = {}

    def push(self, key: Hashable, value: int) -> None:
        self._pending[key] = value

    def due(self, now: float) -> list[tuple[Hashable, int]]:
        ready = []
        for key, value in list(self._pending.items()):
            # Tolerance: float subtraction (1.2 - 1.0) lands just below the interval.
            if now - self._last_sent.get(key, float("-inf")) >= self._interval - 1e-9:
                ready.append((key, value))
                self._last_sent[key] = now
                del self._pending[key]
        return ready

    def has_pending(self) -> bool:
        return bool(self._pending)

    def is_pending(self, key: Hashable) -> bool:
        return key in self._pending
