"""COJI Bluetooth constants.

Command bytes and GATT UUIDs come from the WowWee COJI Android library
(`coji-library.jar`) and the public iOS SDK headers. Framing matches the
WowWee MiP module: write raw bytes to FFE9, read ASCII-hex notifications
on FFE4.
"""

from __future__ import annotations

DOMAIN = "coji"
MANUFACTURER = "WowWee"
MODEL = "COJI"

# First two manufacturer-data bytes are a big-endian product id.
# 0x00 0x2F == 47. Bluetooth stacks treat those bytes as a little-endian
# company id, which is what Home Assistant matches on.
PRODUCT_ID = 47
MANUFACTURER_ID = 0x2F00

CHAR_TX = "0000ffe9-0000-1000-8000-00805f9b34fb"
CHAR_RX = "0000ffe4-0000-1000-8000-00805f9b34fb"

# Java `byte` constants from CojiCommandValues, stored unsigned.
CMD_PLAY_SOUND = 0x06
CMD_GET_FIRMWARE = 0x14
CMD_SET_VOLUME = 0x21
CMD_GET_VOLUME = 0x22
CMD_SET_BACKLIGHT = 0x24
CMD_GET_BACKLIGHT = 0x25
CMD_REBOOT = 0x31
CMD_POWER_OFF = 0x32
CMD_DRIVE_FORWARD = 0x71
CMD_DRIVE_BACKWARD = 0x72
CMD_TURN_LEFT = 0x73
CMD_TURN_RIGHT = 0x74
CMD_PLAY_ANIMATION = 0x83
CMD_SHOW_IMAGE = 0x84
CMD_STOP = 0x89
CMD_BUTTON = 0x90
CMD_ACCEL = 0x92
CMD_BATTERY = 0xA0
CMD_GET_CHEST = 0xB0
CMD_SET_CHEST = 0xB1

STOP_ANIMATION = 0x01
STOP_SOUND = 0x02

# iOS sample drives in 0.16s bursts. The device clock is 8ms ticks.
DRIVE_BURST_SECONDS = 0.16
DRIVE_TICK_SECONDS = 0.008

# Battery ADC from CojiRobot.handleReceivedCojiCommand:
# volts = uint16 * 0.00322 * 3
BATTERY_SCALE = 0.00322 * 3.0
VOLUME_STEPS = 50

SERVICE_DRIVE = "drive"
SERVICE_PLAY_SOUND = "play_sound"
SERVICE_PLAY_ANIMATION = "play_animation"
SERVICE_SHOW_IMAGE = "show_image"
SERVICE_STOP = "stop"

# On-device paths from CojiRobot.soundPathList / animationPathList / imagePathList.
SOUNDS: dict[str, str] = {
    "pop": r"s\NA_Sfx_Pop.wav",
    "receive": r"s\A_Sfx_Receive.wav",
    "bark": r"s\R_SFX_Bark 1 1.wav",
    "meow": r"s\R_SFX_Meow 2 1.wav",
    "roar": r"s\R_SFX_Roar 2 1.wav",
    "giggle": r"s\R_Sfx_Giggle.wav",
    "beep": r"s\R_Sfx_Beep 1.wav",
    "siren": r"s\R_Sfx_Siren 1.wav",
    "yawn": r"s\R_SFX_Yawn 1.wav",
    "wowwee": r"s\R_Sfx_WowWee.wav",
    "coji": r"s\R_SFX_Coji_Coji_1.wav",
    "laugh": r"s\R_Sfx_Laugh_3.wav",
    "trumpet": r"s\R_SFX_Trumpet 1.wav",
    "rocket": r"s\R_Sfx_Rocket_Blast_Off 1.wav",
    "snore": r"s\R_Sfx_Snore.wav",
}

ANIMATIONS: dict[str, str] = {
    "character_1": r"ani\c\001.txt",
    "character_2": r"ani\c\002.txt",
    "character_5": r"ani\c\005.txt",
    "default_1": r"ani\d\001.txt",
    "emoji_1": r"ani\e\001.txt",
    "emoji_2": r"ani\e\002.txt",
    "reward_1": r"ani\r\001.txt",
    "tool_1": r"ani\t\001.txt",
    "vehicle_1": r"ani\v\001.txt",
    "vehicle_2": r"ani\v\002.txt",
}

IMAGES: dict[str, str] = {
    "cat": r"img\c\1F408.jpg",
    "robot": r"img\c\1f916.jpg",
    "smile": r"img\d\1f603.jpg",
    "heart": r"img\d\1f49c.jpg",
    "eyes": r"img\e\Eyes_1.jpg",
    "wink": r"img\e\Eyes_Wink.jpg",
    "sleep": r"img\e\Eyes_sleepA.jpg",
    "car": r"img\v\1F692_A.jpg",
    "rocket": r"img\v\1F680.jpg",
    "blank": r"img\c\Blank.jpg",
}

# kCojiImage_AnimationTemplate
IMAGE_TEMPLATES: dict[str, int] = {
    "scale_up": 0x00,
    "scale_down": 0x01,
    "right_to_left": 0x02,
    "left_to_right": 0x03,
    "center_to_left": 0x04,
    "center_to_right": 0x05,
    "down_to_center": 0x06,
    "center_to_down": 0x07,
    "up_to_center": 0x08,
    "center_to_up": 0x09,
    "none": 0x0A,
}

ATTITUDE_KEYS = (
    "tilt_left",
    "tilt_right",
    "tilt_forward",
    "tilt_backward",
    "lie_forward",
    "lie_backward",
    "shake",
    "pickup",
)
