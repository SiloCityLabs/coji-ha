# COJI BLE protocol

Extracted from WowWee's public SDKs. The closed Android library is `coji-library.jar` in [COJI-Android-SDK](https://github.com/WowWeeLabs/COJI-Android-SDK). The iOS headers in [COJI-iOS-SDK](https://github.com/WowWeeLabs/COJI-iOS-SDK) name the same commands. The radio itself is the WowWee BLE module also documented for MiP in [MiP-BLE-Protocol](https://github.com/WowWeeLabs/MiP-BLE-Protocol).

## Discovery

Manufacturer data starts with a big-endian product id. COJI is **47** (`0x00 0x2F`).

Bluetooth stacks read those two bytes as a little-endian company identifier, so Home Assistant sees manufacturer id **12032** (`0x2F00`). MiP is product id 5, which shows up as manufacturer id 1280 and is ignored here.

The finder also accepts a local name containing `COJI`.

## GATT

| Role | UUID |
|------|------|
| Send service | `0000ffe5-0000-1000-8000-00805f9b34fb` |
| TX write | `0000ffe9-0000-1000-8000-00805f9b34fb` |
| Receive service | `0000ffe0-0000-1000-8000-00805f9b34fb` |
| RX notify | `0000ffe4-0000-1000-8000-00805f9b34fb` |

Writes are raw bytes, chunked at 20 bytes. Notifications are ASCII hex (two characters per byte), same as MiP. A notification that contains a byte above `0x7F` is raw binary instead.

The first decoded byte is the command. The rest is the payload.

## Commands

| Command | Byte | Payload |
|---------|------|---------|
| Play sound | `0x06` | clip id, path length, ASCII path |
| Firmware | `0x14` | none. Reply bytes are concatenated as signed decimals |
| Set volume | `0x21` | 0–50 |
| Get volume | `0x22` | reply is one byte, 0–50 |
| Set backlight | `0x24` | 0 or 1 |
| Get backlight | `0x25` | reply is 0 or 1 |
| Reboot | `0x31` | mode `1` (application) |
| Power off | `0x32` | none |
| Drive forward | `0x71` | speed 0–100, time in 8ms ticks |
| Drive backward | `0x72` | speed, time |
| Turn left | `0x73` | **time, speed** (swapped) |
| Turn right | `0x74` | **time, speed** (swapped) |
| Play animation | `0x83` | sound flag, clip id, path length, path |
| Show image | `0x84` | duration 0–30, template, clip id, path length, path |
| Stop | `0x89` | 1 animation, 2 sound, 3 file transfer |
| Buttons | `0x90` | left, center, right. 1 means pressed |
| Accelerometer | `0x92` | tilt L/R/forward/back, lie forward/back, shake, pickup |
| Battery | `0xA0` | uint16. Volts = count × 0.00322 × 3 |
| Get chest LED | `0xB0` | red, green, blue. 255 is on |
| Set chest LED | `0xB1` | red, green, blue. 0 or 255 |

Speed in the SDK is `int(clamp(speed, 0, 1) * 100)`. Time is `int(seconds / 0.008)`, clamped to 1–255.

Animation sound flag is **0 to enable sound** and **1 to mute**. That matches `CojiRobot.playAnimation`.

Paths use backslashes, for example `s\R_Sfx_Beep 1.wav`, `ani\e\001.txt`, `img\d\1f603.jpg`.

## What this integration does not do

File upload, directory listing, and firmware update are in the SDK and are not implemented. Continuous drive (`0x78`) has an enum in the library and no public method, so drive stays timed.
