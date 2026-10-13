"""Run monitor jobs off the GUI thread, one at a time, in submission order."""

import logging
from collections.abc import Callable
from typing import Any, Protocol

from PySide6.QtCore import QObject, QThread, Signal, Slot

log = logging.getLogger(__name__)


class Executor(Protocol):
    def submit(self, job: Callable[[], Any], done: Callable[[Any], None] | None = None) -> None: ...


class ImmediateExecutor:
    """Runs jobs synchronously; used in tests."""

    def submit(self, job: Callable[[], Any], done: Callable[[Any], None] | None = None) -> None:
        result = job()
        if done is not None:
            done(result)


class _Worker(QObject):
    finished = Signal(object, object)  # done callback, result

    @Slot(object, object)
    def run(self, job: Callable[[], Any], done: Callable[[Any], None] | None) -> None:
        try:
            result = job()
        except Exception:
            log.exception("monitor job failed")
            result = None
        self.finished.emit(done, result)


class QtWorkerExecutor(QObject):
    _request = Signal(object, object)

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._thread = QThread()
        self._thread.setObjectName("ddc-worker")
        self._worker = _Worker()
        self._worker.moveToThread(self._thread)
        self._request.connect(self._worker.run)
        self._worker.finished.connect(self._deliver)
        self._thread.start()

    def submit(self, job: Callable[[], Any], done: Callable[[Any], None] | None = None) -> None:
        self._request.emit(job, done)

    def shutdown(self) -> None:
        self._thread.quit()
        # A ddcutil call may run up to 2 x 10 s; destroying a running QThread aborts the process.
        self._thread.wait(25000)

    @Slot(object, object)
    def _deliver(self, done: Callable[[Any], None] | None, result: Any) -> None:
        if done is not None:
            done(result)
