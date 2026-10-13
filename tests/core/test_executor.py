import threading
import time

from benq_monitor_control.core.executor import ImmediateExecutor, QtWorkerExecutor


def wait_for(qapp, predicate, timeout=5.0):
    deadline = time.monotonic() + timeout
    while not predicate() and time.monotonic() < deadline:
        qapp.processEvents()
        time.sleep(0.01)


def test_immediate_executor():
    seen = []
    ImmediateExecutor().submit(lambda: 42, seen.append)
    assert seen == [42]


def test_qt_worker_runs_jobs_in_order_off_main_thread(qapp):
    executor = QtWorkerExecutor()
    main = threading.get_ident()
    seen = []
    for i in range(3):
        executor.submit(lambda i=i: (i, threading.get_ident()), seen.append)
    wait_for(qapp, lambda: len(seen) == 3)
    executor.shutdown()
    assert [r[0] for r in seen] == [0, 1, 2]
    assert all(r[1] != main for r in seen)


def test_qt_worker_delivers_none_on_exception(qapp):
    executor = QtWorkerExecutor()
    seen = []
    executor.submit(lambda: 1 / 0, seen.append)
    wait_for(qapp, lambda: len(seen) == 1)
    executor.shutdown()
    assert seen == [None]


def test_shutdown_waits_for_a_running_job(qapp):
    executor = QtWorkerExecutor()
    executor.submit(lambda: time.sleep(4))
    time.sleep(0.2)
    executor.shutdown()
    assert executor._thread.isFinished()
