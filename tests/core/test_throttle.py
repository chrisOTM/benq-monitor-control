from benq_monitor_control.core.throttle import Coalescer


def test_keeps_only_latest_value_per_key():
    c = Coalescer(0.2)
    for v in (10, 20, 30):
        c.push("brightness", v)
    assert c.due(0.0) == [("brightness", 30)]
    assert not c.has_pending()


def test_respects_interval_per_key():
    c = Coalescer(0.2)
    c.push("brightness", 10)
    assert c.due(1.0) == [("brightness", 10)]
    c.push("brightness", 20)
    c.push("volume", 5)
    assert c.due(1.1) == [("volume", 5)]
    assert c.has_pending()
    assert c.due(1.2) == [("brightness", 20)]
