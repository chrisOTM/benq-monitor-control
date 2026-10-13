"""BenQ MA320U — v1 features, verified live on 2026-10-13 (tests/fixtures/ddcutil-2026-10-13)."""

from .model import Choice, Feature, FeatureSpec, Kind, MonitorModel

PICTURE_MODES = (
    Choice(0x0F, "Tux-Book"),  # BenQ: M-Book
    Choice(0x0A, "sRGB"),
    Choice(0x22, "Display P3"),  # inferred: gamut switches to 0x03
    Choice(0x32, "Cinema"),
    Choice(0x28, "Game"),
    Choice(0x12, "User"),
)

INPUTS = (
    Choice(0x0F, "DisplayPort"),
    Choice(0x11, "HDMI 1"),
    Choice(0x12, "HDMI 2"),
    Choice(0x13, "USB-C"),  # value read while connected via USB-C
    Choice(0x15, "Input 0x15"),  # listed in the capabilities, not identified
)

MA320U = MonitorModel(
    model_name="BenQ MA320U",
    display_name="BenQ MA320U",
    features=(
        FeatureSpec(Feature.PICTURE_MODE, 0xDC, Kind.CHOICE, choices=PICTURE_MODES, polled=True),
        FeatureSpec(Feature.BRIGHTNESS, 0x10, Kind.RANGE, polled=True),
        FeatureSpec(Feature.VOLUME, 0x62, Kind.RANGE, polled=True),
        FeatureSpec(Feature.INPUT_SOURCE, 0x60, Kind.CHOICE, choices=INPUTS, polled=True),
        FeatureSpec(Feature.LOW_BLUE_LIGHT, 0x19, Kind.RANGE),
        FeatureSpec(Feature.BRIGHTNESS_INTELLIGENCE, 0x81, Kind.TOGGLE),
    ),
    hdr_modes=frozenset({0x23, 0x27}),
    hdr_locks=frozenset(
        {Feature.PICTURE_MODE, Feature.BRIGHTNESS, Feature.LOW_BLUE_LIGHT, Feature.BRIGHTNESS_INTELLIGENCE}
    ),
    # Hardware check 2026-10-13: Low Blue Light is rejected in sRGB and Display P3;
    # everything else is accepted in every SDR mode.
    locks={0x0A: frozenset({Feature.LOW_BLUE_LIGHT}), 0x22: frozenset({Feature.LOW_BLUE_LIGHT})},
)
