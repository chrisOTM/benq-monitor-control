"""Persist scenarios as JSON; a broken file is set aside, never overwritten silently."""

import json
import logging
import time
from collections.abc import Sequence
from pathlib import Path

from ..config.atomic import write_json_atomic
from .scenario import Scenario, scenario_from_dict, scenario_to_dict

log = logging.getLogger(__name__)
FORMAT_VERSION = 1


class ScenarioStore:
    def __init__(self, path: Path) -> None:
        self.path = path

    def load(self) -> list[Scenario]:
        if not self.path.exists():
            return []
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
            if not isinstance(data, dict) or data.get("version") != FORMAT_VERSION:
                raise ValueError("unsupported file format")
            items = data.get("scenarios")
            if not isinstance(items, list):
                raise ValueError("scenarios must be a list")
            return [scenario_from_dict(item) for item in items]
        except (OSError, ValueError) as exc:  # json.JSONDecodeError is a ValueError
            backup = self.path.with_name(f"{self.path.name}.corrupt-{int(time.time())}")
            self.path.replace(backup)
            log.warning("could not read %s (%s); moved it to %s", self.path, exc, backup)
            return []

    def save(self, scenarios: Sequence[Scenario]) -> None:
        write_json_atomic(
            self.path, {"version": FORMAT_VERSION, "scenarios": [scenario_to_dict(s) for s in scenarios]}
        )
