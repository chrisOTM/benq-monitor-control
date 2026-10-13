"""Data description of a monitor's controllable features."""

from collections.abc import Mapping
from dataclasses import dataclass, field
from enum import StrEnum


class Feature(StrEnum):
    PICTURE_MODE = "picture_mode"
    BRIGHTNESS = "brightness"
    VOLUME = "volume"
    INPUT_SOURCE = "input_source"
    LOW_BLUE_LIGHT = "low_blue_light"
    BRIGHTNESS_INTELLIGENCE = "brightness_intelligence"


class Kind(StrEnum):
    RANGE = "range"
    CHOICE = "choice"
    TOGGLE = "toggle"


@dataclass(frozen=True)
class Choice:
    value: int
    label: str


@dataclass(frozen=True)
class FeatureSpec:
    feature: Feature
    code: int
    kind: Kind
    minimum: int = 0
    maximum: int | None = None  # None: use the maximum the monitor reports
    choices: tuple[Choice, ...] = ()
    polled: bool = False  # can change on the monitor itself; re-read periodically


@dataclass(frozen=True)
class MonitorModel:
    model_name: str
    display_name: str
    features: tuple[FeatureSpec, ...]
    hdr_modes: frozenset[int] = frozenset()
    hdr_locks: frozenset[Feature] = frozenset()
    locks: Mapping[int, frozenset[Feature]] = field(default_factory=dict)
    firmware_code: int = 0xC9

    def spec(self, feature: Feature) -> FeatureSpec:
        for spec in self.features:
            if spec.feature is feature:
                return spec
        raise KeyError(feature)

    def codes(self, polled_only: bool = False) -> list[int]:
        return [s.code for s in self.features if s.polled or not polled_only]

    def is_locked(self, feature: Feature, mode: int | None) -> bool:
        if mode in self.hdr_modes:
            return feature in self.hdr_locks
        return feature in self.locks.get(mode, frozenset())

    def choice_label(self, feature: Feature, value: int) -> str | None:
        for choice in self.spec(feature).choices:
            if choice.value == value:
                return choice.label
        return None
