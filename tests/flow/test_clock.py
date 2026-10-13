from benq_monitor_control.flow.clock import ClockWatch


def test_first_tick_is_baseline():
    assert ClockWatch().tick(1000.0, 50.0) is False


def test_normal_progress_is_not_a_jump():
    watch = ClockWatch()
    watch.tick(1000.0, 50.0)
    assert watch.tick(1060.0, 110.0) is False


def test_suspend_is_a_jump():
    watch = ClockWatch()
    watch.tick(1000.0, 50.0)
    # Monotonic time does not advance during suspend; wall time does.
    assert watch.tick(1000.0 + 3 * 3600, 110.0) is True
    assert watch.tick(1000.0 + 3 * 3600 + 60, 170.0) is False
