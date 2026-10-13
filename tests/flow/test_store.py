import json

from benq_monitor_control.flow.scenario import new_scenario
from benq_monitor_control.flow.store import ScenarioStore


def test_missing_file_loads_empty(tmp_path):
    assert ScenarioStore(tmp_path / "scenarios.json").load() == []


def test_save_and_load(tmp_path):
    store = ScenarioStore(tmp_path / "cfg" / "scenarios.json")
    scenarios = [new_scenario("Day"), new_scenario("Evening")]
    store.save(scenarios)
    assert store.load() == scenarios
    data = json.loads((tmp_path / "cfg" / "scenarios.json").read_text())
    assert data["version"] == 1 and len(data["scenarios"]) == 2
    assert not list((tmp_path / "cfg").glob("*.tmp"))


def test_corrupt_file_is_backed_up_and_ignored(tmp_path):
    path = tmp_path / "scenarios.json"
    path.write_text('{"version": 1, "scenarios": [{"id": "x"}]}')  # missing name
    store = ScenarioStore(path)
    assert store.load() == []
    backups = list(tmp_path.glob("scenarios.json.corrupt-*"))
    assert len(backups) == 1
    assert '"id": "x"' in backups[0].read_text()
    assert not path.exists()


def test_invalid_json_is_backed_up(tmp_path):
    path = tmp_path / "scenarios.json"
    path.write_text("{not json")
    assert ScenarioStore(path).load() == []
    assert len(list(tmp_path.glob("scenarios.json.corrupt-*"))) == 1
