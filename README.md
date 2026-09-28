# COJI – Home Assistant

Custom Home Assistant integration for the **WowWee COJI** robot. Control is local Bluetooth Low Energy. No WowWee account.

**Maintained by [SiloCityLabs](https://github.com/SiloCityLabs/coji-ha).**

Protocol notes are in [`PROTOCOL.md`](PROTOCOL.md). They were taken from the public [COJI Android SDK](https://github.com/WowWeeLabs/COJI-Android-SDK) (`coji-library.jar`), the [COJI iOS SDK](https://github.com/WowWeeLabs/COJI-iOS-SDK) headers, and the shared WowWee module layout in the [MiP BLE protocol](https://github.com/WowWeeLabs/MiP-BLE-Protocol).

## Features

- **Local BLE** — connect, send a command, disconnect
- **Drive** — forward, back, left, right (timed bursts)
- **Chest LED** — red, green, and blue, each fully on or off
- **Backlight** — screen backlight
- **Volume** — 0–100, mapped to the robot's 0–50 steps
- **Sounds, animations, and pictures** — built-in clip names, or a raw on-device path
- **Battery voltage**, firmware version, head buttons, tilt / shake / pickup
- Services: `drive`, `play_sound`, `play_animation`, `show_image`, `stop`

## Requirements

- Home Assistant with Bluetooth (USB adapter and/or an ESPHome `bluetooth_proxy` with `active: true`)
- A COJI that is advertising. The integration matches the name `COJI` or WowWee product id **47** (manufacturer id `12032`)
- The phone app holds the radio while it is connected. Disconnect COJI in the WowWee app before Home Assistant can drive it

## Installation (HACS)

1. HACS → ⋮ → **Custom repositories**
2. URL: `https://github.com/SiloCityLabs/coji-ha`  
   Category: **Integration**
3. Download **COJI** → restart Home Assistant

Manual install: copy `custom_components/coji` into `/config/custom_components/`, then restart.

## Setup

1. Turn COJI on so it advertises
2. **Settings → Devices & Services → Add Integration → COJI**
3. Confirm the discovered robot

Home Assistant polls about once a minute for battery, volume, backlight, and the chest LED. Drive buttons and the clip menus connect only when you use them.

## Drive

Buttons send a full-speed burst of **0.16 seconds**, the same length as the WowWee sample app. For a different speed or duration:

```yaml
action: coji.drive
target:
  device_id: YOUR_COJI_DEVICE_ID
data:
  direction: forward
  speed: 0.6
  seconds: 0.4
```

`direction` is `forward`, `backward`, `left`, or `right`. `speed` is 0–1. `seconds` is clamped to the robot's 8ms ticks (about 2 seconds max).

## Clips

Selects play as soon as you pick an option. Names include `bark`, `meow`, `giggle`, `emoji_1`, `smile`, `rocket`. A service can also send a path from the robot's filesystem:

```yaml
action: coji.play_sound
target:
  device_id: YOUR_COJI_DEVICE_ID
data:
  sound: bark
```

```yaml
action: coji.show_image
target:
  device_id: YOUR_COJI_DEVICE_ID
data:
  image: smile
  template: scale_up
  duration: 0
```

`template` is one of `none`, `scale_up`, `scale_down`, `right_to_left`, `left_to_right`, `center_to_left`, `center_to_right`, `down_to_center`, `center_to_down`, `up_to_center`, `center_to_up`.

## Bluetooth behavior

- Writes raw command bytes to `0000ffe9-0000-1000-8000-00805f9b34fb`
- Reads ASCII-hex notifications from `0000ffe4-0000-1000-8000-00805f9b34fb`
- Long writes are split into 20-byte chunks
- Head-button and tilt reports only arrive while a connection is open (a poll or a command)

## Development

```bash
git clone git@github.com:SiloCityLabs/coji-ha.git
cd coji-ha
python3 -m pip install -r requirements-test.txt
pytest
```

## Credits

- [WowWee COJI Android SDK](https://github.com/WowWeeLabs/COJI-Android-SDK) and [iOS SDK](https://github.com/WowWeeLabs/COJI-iOS-SDK) — command bytes, on-device file paths, product id 47 (Apache-2.0)
- [WowWee MiP BLE protocol](https://github.com/WowWeeLabs/MiP-BLE-Protocol) — shared GATT services and ASCII-hex replies
- SiloCityLabs — Home Assistant integration

## License

MIT — see [`LICENSE`](LICENSE). The WowWee SDKs this was read from are Apache-2.0.
