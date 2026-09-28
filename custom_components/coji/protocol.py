"""COJI packet builders and notification parsers."""

from __future__ import annotations

from collections.abc import Mapping

from .const import (
    ATTITUDE_KEYS,
    BATTERY_SCALE,
    CMD_DRIVE_BACKWARD,
    CMD_DRIVE_FORWARD,
    CMD_PLAY_ANIMATION,
    CMD_PLAY_SOUND,
    CMD_SET_BACKLIGHT,
    CMD_SET_CHEST,
    CMD_SET_VOLUME,
    CMD_SHOW_IMAGE,
    CMD_STOP,
    CMD_TURN_LEFT,
    CMD_TURN_RIGHT,
    DRIVE_TICK_SECONDS,
    IMAGE_TEMPLATES,
    PRODUCT_ID,
    VOLUME_STEPS,
)

_DRIVE = {
    "forward": CMD_DRIVE_FORWARD,
    "backward": CMD_DRIVE_BACKWARD,
    "left": CMD_TURN_LEFT,
    "right": CMD_TURN_RIGHT,
}

_HEX = set("0123456789abcdefABCDEF")


def product_id_from_manufacturer(manufacturer_data: Mapping[int, bytes]) -> int | None:
    """Return the WowWee product id encoded in an advertisement.

    Home Assistant stores the first two AD manufacturer bytes as a
    little-endian company id. The COJI SDK reads those same bytes as a
    big-endian product id (47).
    """
    for company_id in manufacturer_data:
        first = company_id & 0xFF
        second = (company_id >> 8) & 0xFF
        return (first << 8) | second
    return None


def is_coji(name: str | None, manufacturer_data: Mapping[int, bytes]) -> bool:
    """True when the advertisement is a COJI (name or product id 47)."""
    if name and "coji" in name.lower():
        return True
    return product_id_from_manufacturer(manufacturer_data) == PRODUCT_ID


def drive_axes(speed: float, seconds: float) -> tuple[int, int]:
    """Map a 0–1 speed and a duration to the device's speed byte and 8ms ticks."""
    speed_value = int(min(max(speed, 0.0), 1.0) * 100)
    ticks = int(seconds / DRIVE_TICK_SECONDS)
    ticks = min(max(ticks, 1), 255)
    return speed_value, ticks


def build_drive(direction: str, speed: float = 1.0, seconds: float = 0.16) -> bytes:
    """Timed drive command.

    Forward and backward are (speed, time). Left and right are (time, speed).
    That swap is what CojiRobot.turnLeftWithSpeed / turnRightWithSpeed send.
    """
    command = _DRIVE.get(direction)
    if command is None:
        raise ValueError(f"Unknown drive direction {direction!r}")
    speed_value, ticks = drive_axes(speed, seconds)
    if direction in ("left", "right"):
        return bytes((command, ticks, speed_value))
    return bytes((command, speed_value, ticks))


def build_volume(percent: float) -> bytes:
    """Volume set. Device range is 0–50; percent is 0–100."""
    level = int(min(max(percent, 0.0), 100.0) / 100.0 * VOLUME_STEPS)
    return bytes((CMD_SET_VOLUME, level))


def volume_percent(level: int) -> int:
    """Device volume byte (0–50) to a 0–100 percent."""
    clamped = min(max(level, 0), VOLUME_STEPS)
    return round(clamped / VOLUME_STEPS * 100)


def build_backlight(enabled: bool) -> bytes:
    """LCD backlight on (1) or off (0)."""
    return bytes((CMD_SET_BACKLIGHT, 0x01 if enabled else 0x00))


def build_chest(red: bool, green: bool, blue: bool) -> bytes:
    """Chest LED. Each channel is fully on (255) or off (0)."""
    return bytes(
        (
            CMD_SET_CHEST,
            0xFF if red else 0x00,
            0xFF if green else 0x00,
            0xFF if blue else 0x00,
        )
    )


def build_stop(kind: int) -> bytes:
    """Stop animation (1), sound (2), or a file transfer (3)."""
    return bytes((CMD_STOP, kind & 0xFF))


def resolve_clip(catalog: Mapping[str, str], name_or_path: str) -> str:
    """Catalog key or a raw on-device path."""
    key = name_or_path.strip()
    if key in catalog:
        return catalog[key]
    lowered = key.lower()
    for name, path in catalog.items():
        if name.lower() == lowered:
            return path
    if "\\" in key or key.lower().endswith((".wav", ".txt", ".jpg")):
        return key
    raise KeyError(key)


def _path_packet(command: int, prefix: bytes, path: str) -> bytes:
    encoded = path.encode("ascii")
    if len(encoded) > 255:
        raise ValueError(f"Path longer than 255 bytes: {path}")
    return bytes((command, *prefix, len(encoded))) + encoded


def build_sound(path: str, clip_id: int = 0) -> bytes:
    """Play a wav that already lives on the robot."""
    return _path_packet(CMD_PLAY_SOUND, bytes((clip_id & 0xFF,)), path)


def build_animation(path: str, *, sound: bool = True, clip_id: int = 0) -> bytes:
    """Play an animation file.

    The SDK sends 0 when sound should play and 1 when it should not.
    """
    sound_flag = 0x00 if sound else 0x01
    return _path_packet(
        CMD_PLAY_ANIMATION,
        bytes((sound_flag, clip_id & 0xFF)),
        path,
    )


def build_image(
    path: str,
    *,
    template: str | int = "none",
    duration: int = 0,
    clip_id: int = 0,
) -> bytes:
    """Show a jpeg that already lives on the robot."""
    if isinstance(template, str):
        if template not in IMAGE_TEMPLATES:
            raise KeyError(template)
        template_id = IMAGE_TEMPLATES[template]
    else:
        template_id = int(template)
    duration_byte = min(max(int(duration), 0), 30)
    return _path_packet(
        CMD_SHOW_IMAGE,
        bytes((duration_byte, template_id & 0xFF, clip_id & 0xFF)),
        path,
    )


def battery_voltage(payload: bytes) -> float:
    """SDK voltage: big-endian ADC count * 0.00322 * 3."""
    if len(payload) < 2:
        raise ValueError("Battery payload needs 2 bytes")
    raw = ((payload[0] & 0xFF) << 8) | (payload[1] & 0xFF)
    return raw * BATTERY_SCALE


def format_firmware(payload: bytes) -> str:
    """Android SDK version: each reply byte as a signed decimal, concatenated.

    ``Byte.toString`` on the payload, not a MiP year/month/day stamp.
    """
    if not payload:
        return ""
    return "".join(str(byte if byte < 128 else byte - 256) for byte in payload)


def parse_attitude(payload: bytes) -> dict[str, bool]:
    """Eight accelerometer flags from the iOS delegate order."""
    flags = [(byte & 0xFF) == 1 for byte in payload]
    return {
        key: flags[index] if index < len(flags) else False
        for index, key in enumerate(ATTITUDE_KEYS)
    }


def attitude_summary(flags: Mapping[str, bool]) -> str:
    """Single state string. Pickup wins over shake, which wins over tilt."""
    for key in (
        "pickup",
        "shake",
        "lie_forward",
        "lie_backward",
        "tilt_left",
        "tilt_right",
        "tilt_forward",
        "tilt_backward",
    ):
        if flags.get(key):
            return key
    if flags:
        return "level"
    return "unknown"


def feed_rx(buffer: bytearray, data: bytes) -> list[tuple[int, bytes]]:
    """Fold one GATT notification into (command, payload) tuples.

    Replies are ASCII hex, same as MiP. A byte with the high bit set is
    raw binary instead (the Android receive service does the same check).
    """
    if not data:
        return []
    if any(byte >= 0x80 for byte in data):
        raw = bytes(buffer) + data
        buffer.clear()
        return [(raw[0], raw[1:])]

    buffer.extend(data)
    try:
        text = bytes(buffer).decode("ascii")
    except UnicodeDecodeError:
        raw = bytes(buffer)
        buffer.clear()
        return [(raw[0], raw[1:])]

    compact = "".join(text.split())
    if (
        len(compact) < 2
        or len(compact) % 2
        or any(char not in _HEX for char in compact)
    ):
        if any(char not in _HEX and not char.isspace() for char in text):
            raw = bytes(buffer)
            buffer.clear()
            return [(raw[0], raw[1:])]
        return []

    raw = bytes.fromhex(compact)
    buffer.clear()
    if not raw:
        return []
    return [(raw[0], raw[1:])]
