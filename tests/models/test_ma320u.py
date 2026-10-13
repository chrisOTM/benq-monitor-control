from benq_monitor_control.models.ma320u import MA320U
from benq_monitor_control.models.model import Feature, Kind


def test_feature_codes():
    assert MA320U.spec(Feature.PICTURE_MODE).code == 0xDC
    assert MA320U.spec(Feature.BRIGHTNESS).code == 0x10
    assert MA320U.spec(Feature.VOLUME).code == 0x62
    assert MA320U.spec(Feature.INPUT_SOURCE).code == 0x60
    assert MA320U.spec(Feature.LOW_BLUE_LIGHT).code == 0x19
    assert MA320U.spec(Feature.BRIGHTNESS_INTELLIGENCE).code == 0x81
    assert MA320U.spec(Feature.BRIGHTNESS_INTELLIGENCE).kind is Kind.TOGGLE


def test_only_v1_codes_are_known():
    assert sorted(MA320U.codes()) == sorted([0xDC, 0x10, 0x62, 0x60, 0x19, 0x81])
    assert sorted(MA320U.codes(polled_only=True)) == sorted([0xDC, 0x10, 0x62, 0x60])


def test_picture_mode_labels():
    labels = [c.label for c in MA320U.spec(Feature.PICTURE_MODE).choices]
    assert labels == ["Tux-Book", "sRGB", "Display P3", "Cinema", "Game", "User"]
    assert MA320U.choice_label(Feature.PICTURE_MODE, 0x0F) == "Tux-Book"
    assert MA320U.choice_label(Feature.PICTURE_MODE, 0x23) is None


def test_hdr_locks():
    for feature in (Feature.PICTURE_MODE, Feature.BRIGHTNESS, Feature.LOW_BLUE_LIGHT, Feature.BRIGHTNESS_INTELLIGENCE):
        assert MA320U.is_locked(feature, 0x23)
        assert MA320U.is_locked(feature, 0x27)
    assert not MA320U.is_locked(Feature.VOLUME, 0x23)
    assert not MA320U.is_locked(Feature.LOW_BLUE_LIGHT, 0x0F)


def test_low_blue_light_locked_in_colour_accurate_modes():
    # Hardware check 2026-10-13: the monitor rejects Low Blue Light in sRGB and Display P3.
    assert MA320U.is_locked(Feature.LOW_BLUE_LIGHT, 0x0A)
    assert MA320U.is_locked(Feature.LOW_BLUE_LIGHT, 0x22)
    for mode in (0x0F, 0x12, 0x28, 0x32):
        assert not MA320U.is_locked(Feature.LOW_BLUE_LIGHT, mode)
    assert not MA320U.is_locked(Feature.BRIGHTNESS, 0x0A)
