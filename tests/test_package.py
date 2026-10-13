import benq_monitor_control
from benq_monitor_control.__main__ import main


def test_version():
    assert benq_monitor_control.__version__ == "0.1.0"


def test_main_is_callable():
    assert callable(main)
