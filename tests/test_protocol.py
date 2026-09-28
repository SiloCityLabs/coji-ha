"""Tests for COJI packet encoding."""

from custom_components.coji.const import (
    CMD_DRIVE_FORWARD,
    CMD_PLAY_ANIMATION,
    CMD_PLAY_SOUND,
    CMD_SET_CHEST,
    CMD_SET_VOLUME,
    CMD_SHOW_IMAGE,
    CMD_TURN_LEFT,
    MANUFACTURER_ID,
    SOUNDS,
)
from custom_components.coji.protocol import (
    attitude_summary,
    battery_voltage,
    build_animation,
    build_chest,
    build_drive,
    build_image,
    build_sound,
    build_volume,
    feed_rx,
    format_firmware,
    is_coji,
    parse_attitude,
    product_id_from_manufacturer,
    resolve_clip,
    volume_percent,
)


def test_product_id_is_big_endian_manufacturer_bytes():
    """Company id 12032 is bytes 00 2F, which the SDK reads as product 47."""
    assert MANUFACTURER_ID == 12032
    assert product_id_from_manufacturer({MANUFACTURER_ID: b"\x00"}) == 47
    assert is_coji(None, {MANUFACTURER_ID: b""})
    assert is_coji("COJI-12", {})
    assert not is_coji("Mip-14915", {0x0500: b"\x01\x00"})


def test_drive_argument_order():
    """Forward is speed then time. Turns swap those bytes."""
    assert build_drive("forward", 1.0, 0.16) == bytes((CMD_DRIVE_FORWARD, 100, 20))
    assert build_drive("left", 1.0, 0.16) == bytes((CMD_TURN_LEFT, 20, 100))
    assert build_drive("backward", 0.5, 0.008)[1:] == bytes((50, 1))


def test_volume_maps_percent_to_50_steps():
    assert build_volume(100) == bytes((CMD_SET_VOLUME, 50))
    assert build_volume(0) == bytes((CMD_SET_VOLUME, 0))
    assert build_volume(50) == bytes((CMD_SET_VOLUME, 25))
    assert volume_percent(50) == 100
    assert volume_percent(25) == 50


def test_chest_is_full_scale_or_off():
    assert build_chest(True, False, True) == bytes((CMD_SET_CHEST, 255, 0, 255))


def test_sound_and_animation_packets_include_path():
    sound = build_sound(SOUNDS["beep"], clip_id=3)
    path = SOUNDS["beep"].encode("ascii")
    assert sound[0] == CMD_PLAY_SOUND
    assert sound[1] == 3
    assert sound[2] == len(path)
    assert sound[3:] == path

    muted = build_animation(r"ani\e\001.txt", sound=False, clip_id=1)
    assert muted[0] == CMD_PLAY_ANIMATION
    assert muted[1] == 1
    assert muted[2] == 1

    image = build_image(r"img\d\1f603.jpg", template="scale_up", duration=2)
    assert image[0] == CMD_SHOW_IMAGE
    assert image[1:4] == bytes((2, 0, 0))


def test_resolve_clip_accepts_names_and_raw_paths():
    assert resolve_clip(SOUNDS, "Bark") == SOUNDS["bark"]
    assert resolve_clip(SOUNDS, r"s\custom.wav") == r"s\custom.wav"


def test_ascii_hex_notification_and_battery():
    buffer = bytearray()
    parsed = feed_rx(buffer, b"A001F4")
    assert parsed == [(0xA0, bytes((0x01, 0xF4)))]
    assert buffer == bytearray()
    assert round(battery_voltage(bytes((0x01, 0xF4))), 3) == round(500 * 0.00322 * 3, 3)


def test_partial_hex_is_buffered():
    buffer = bytearray()
    assert feed_rx(buffer, b"A") == []
    assert feed_rx(buffer, b"001F4") == [(0xA0, bytes((0x01, 0xF4)))]


def test_firmware_and_attitude():
    assert format_firmware(bytes((0x0E, 0x02, 0x1B, 0x07))) == "2014-02-27 r7"
    flags = parse_attitude(bytes((0, 1, 0, 0, 0, 0, 1, 0)))
    assert flags["tilt_right"]
    assert flags["shake"]
    assert attitude_summary(flags) == "shake"
    assert attitude_summary({"pickup": True, "shake": True}) == "pickup"
