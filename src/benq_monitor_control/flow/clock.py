"""Detect wall-clock jumps (suspend/resume, manual clock changes)."""


class ClockWatch:
    def __init__(self, threshold_s: float = 120.0) -> None:
        self._threshold = threshold_s
        self._last: tuple[float, float] | None = None

    def tick(self, wall: float, mono: float) -> bool:
        if self._last is None:
            self._last = (wall, mono)
            return False
        wall_delta = wall - self._last[0]
        mono_delta = mono - self._last[1]
        self._last = (wall, mono)
        return abs(wall_delta - mono_delta) > self._threshold
