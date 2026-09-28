"""BLE client for a WowWee COJI."""

from __future__ import annotations

import asyncio
import logging
import time
from collections.abc import Awaitable, Callable
from dataclasses import asdict, dataclass, field

from bleak.backends.device import BLEDevice
from bleak_retry_connector import (
    BleakAbortedError,
    BleakClientWithServiceCache,
    BleakConnectionError,
    BleakNotFoundError,
    BleakOutOfConnectionSlotsError,
    establish_connection,
)

from .const import (
    ANIMATIONS,
    CHAR_RX,
    CHAR_TX,
    CMD_ACCEL,
    CMD_BATTERY,
    CMD_BUTTON,
    CMD_GET_BACKLIGHT,
    CMD_GET_CHEST,
    CMD_GET_FIRMWARE,
    CMD_GET_VOLUME,
    CMD_POWER_OFF,
    CMD_REBOOT,
    DRIVE_BURST_SECONDS,
    IMAGES,
    SOUNDS,
    STOP_ANIMATION,
    STOP_SOUND,
)
from .protocol import (
    attitude_summary,
    battery_voltage,
    build_animation,
    build_backlight,
    build_chest,
    build_drive,
    build_image,
    build_sound,
    build_stop,
    build_volume,
    feed_rx,
    format_firmware,
    parse_attitude,
    resolve_clip,
    volume_percent,
)

_LOGGER = logging.getLogger(__name__)

NOTIFY_CHUNK = 20
COMMAND_TIMEOUT = 4.0
# One try. The default is four 20s attempts, which pins the proxy and
# dumps every queued command onto the robot the moment it wakes up.
CONNECT_ATTEMPTS = 1
CONNECT_BACKOFF_SECONDS = 20.0
# Keep the link open briefly so a few button presses share one connection.
SESSION_IDLE_SECONDS = 20.0
# Commands that sat behind a connect or a stuck request are stale.
STALE_AFTER_SECONDS = 3.0
COMMAND_GAP_SECONDS = 0.08

StateListener = Callable[["CojiState"], None]


@dataclass
class CojiState:
    """Last known robot state."""

    battery_voltage: float | None = None
    volume: int | None = None
    backlight: bool | None = None
    chest_red: bool = False
    chest_green: bool = False
    chest_blue: bool = False
    firmware: str | None = None
    left_button: bool | None = None
    center_button: bool | None = None
    right_button: bool | None = None
    attitude: str = "unknown"
    attitude_flags: dict[str, bool] = field(default_factory=dict)
    sound: str | None = None
    animation: str | None = None
    image: str | None = None

    def as_dict(self) -> dict:
        """Coordinator-friendly copy."""
        return asdict(self)

    @property
    def chest_on(self) -> bool:
        """True when any chest channel is lit."""
        return self.chest_red or self.chest_green or self.chest_blue


class CojiClient:
    """One BLE session. Commands reuse it, then the link drops after it goes quiet."""

    def __init__(self, ble_device: BLEDevice) -> None:
        """Init from a Home Assistant BLE device."""
        self.device = ble_device
        self.address = ble_device.address
        self.name = ble_device.name or "COJI"
        self.state = CojiState()

        self._client: BleakClientWithServiceCache | None = None
        self._lock = asyncio.Lock()
        self._notify_started = False
        self._rx_buffer = bytearray()
        self._waiters: dict[int, asyncio.Future[bytes]] = {}
        self._listeners: list[StateListener] = []
        self._backoff_until = 0.0
        self._session = 0
        self._idle_handle: asyncio.TimerHandle | None = None

    def add_listener(self, listener: StateListener) -> None:
        """Register a callback invoked after state changes."""
        self._listeners.append(listener)

    @property
    def chest_rgb(self) -> tuple[int, int, int]:
        """Chest LED as 0/255 channels."""
        return (
            255 if self.state.chest_red else 0,
            255 if self.state.chest_green else 0,
            255 if self.state.chest_blue else 0,
        )

    async def refresh(self) -> CojiState:
        """Read volume, battery, backlight, chest LED, and firmware."""

        async def _do() -> CojiState:
            commands = (
                CMD_GET_VOLUME,
                CMD_BATTERY,
                CMD_GET_BACKLIGHT,
                CMD_GET_CHEST,
            )
            answered = False
            for command in commands:
                try:
                    await self._request(command)
                except TimeoutError:
                    _LOGGER.warning("COJI command 0x%02X timed out", command)
                    if not answered:
                        raise TimeoutError("COJI did not respond") from None
                    break
                answered = True
                await asyncio.sleep(COMMAND_GAP_SECONDS)
            if self.state.firmware is None:
                try:
                    await self._request(CMD_GET_FIRMWARE)
                except TimeoutError:
                    _LOGGER.debug("COJI firmware request timed out")
            return self.state

        return await self._run(_do)

    async def drive(
        self,
        direction: str,
        speed: float = 1.0,
        seconds: float = DRIVE_BURST_SECONDS,
    ) -> None:
        """Drive or turn for a short timed burst."""
        payload = build_drive(direction, speed, seconds)
        await self._run(lambda: self._write(payload))

    async def set_volume(self, percent: float) -> None:
        """Set volume from a 0–100 percent."""
        payload = build_volume(percent)

        async def _do() -> None:
            await self._write(payload)
            self.state.volume = volume_percent(payload[1])
            self._emit()

        await self._run(_do)

    async def set_backlight(self, enabled: bool) -> None:
        """Turn the face backlight on or off."""
        payload = build_backlight(enabled)

        async def _do() -> None:
            await self._write(payload)
            self.state.backlight = enabled
            self._emit()

        await self._run(_do)

    async def set_chest(self, red: bool, green: bool, blue: bool) -> None:
        """Set the chest LED. Channels are on or off."""
        payload = build_chest(red, green, blue)

        async def _do() -> None:
            await self._write(payload)
            self.state.chest_red = red
            self.state.chest_green = green
            self.state.chest_blue = blue
            self._emit()

        await self._run(_do)

    async def play_sound(self, name_or_path: str) -> None:
        """Play a built-in sound by catalog name or on-device path."""
        path = resolve_clip(SOUNDS, name_or_path)
        payload = build_sound(path)

        async def _do() -> None:
            await self._write(payload)
            self.state.sound = _catalog_key(SOUNDS, name_or_path)
            self._emit()

        await self._run(_do)

    async def play_animation(self, name_or_path: str, *, sound: bool = True) -> None:
        """Play a built-in animation."""
        path = resolve_clip(ANIMATIONS, name_or_path)
        payload = build_animation(path, sound=sound)

        async def _do() -> None:
            await self._write(payload)
            self.state.animation = _catalog_key(ANIMATIONS, name_or_path)
            self._emit()

        await self._run(_do)

    async def show_image(
        self,
        name_or_path: str,
        *,
        template: str | int = "none",
        duration: int = 0,
    ) -> None:
        """Show a built-in picture."""
        path = resolve_clip(IMAGES, name_or_path)
        payload = build_image(path, template=template, duration=duration)

        async def _do() -> None:
            await self._write(payload)
            self.state.image = _catalog_key(IMAGES, name_or_path)
            self._emit()

        await self._run(_do)

    async def stop(self) -> None:
        """Stop the current animation and sound."""

        async def _do() -> None:
            await self._write(build_stop(STOP_ANIMATION))
            await self._write(build_stop(STOP_SOUND))

        await self._run(_do)

    async def reboot(self) -> None:
        """Reboot into the application (mode 1)."""
        await self._run(lambda: self._write(bytes((CMD_REBOOT, 0x01))), hold=False)

    async def power_off(self) -> None:
        """Ask the robot to power off."""
        await self._run(lambda: self._write(bytes((CMD_POWER_OFF,))), hold=False)

    async def async_shutdown(self) -> None:
        """Drop the link. Called when the config entry unloads."""
        self._session += 1
        self._cancel_idle()
        async with self._lock:
            await self._disconnect()

    async def _run(self, action: Callable[[], Awaitable], *, hold: bool = True):
        started = time.monotonic()
        async with self._lock:
            waited = time.monotonic() - started
            if waited > STALE_AFTER_SECONDS:
                _LOGGER.warning(
                    "Dropped a COJI command that waited %.1fs",
                    waited,
                )
                raise ConnectionError("COJI was busy; command dropped")
            if time.monotonic() < self._backoff_until:
                raise ConnectionError("COJI is cooling down after a failed connection")
            # Invalidate a disconnect that already left the timer and is
            # waiting to take this lock.
            self._session += 1
            self._cancel_idle()
            try:
                await self._ensure_connected()
                result = await action()
            except (TimeoutError, ConnectionError):
                self._backoff_until = time.monotonic() + CONNECT_BACKOFF_SECONDS
                await self._disconnect()
                raise
            self._backoff_until = 0.0
            if hold:
                self._arm_idle()
            else:
                await self._disconnect()
            return result

    async def _ensure_connected(self) -> None:
        if self._client and self._client.is_connected:
            if not self._notify_started:
                await self._start_notify()
            return
        try:
            _LOGGER.info("Connecting to COJI %s", self.address)
            client = await establish_connection(
                BleakClientWithServiceCache,
                self.device,
                self.address,
                disconnected_callback=self._client_disconnected,
                max_attempts=CONNECT_ATTEMPTS,
            )
            _LOGGER.info("Connected to COJI %s", self.address)
        except (
            BleakNotFoundError,
            BleakOutOfConnectionSlotsError,
            BleakAbortedError,
            BleakConnectionError,
        ) as err:
            self._client = None
            raise ConnectionError(str(err)) from err
        self._client = client
        self._rx_buffer.clear()
        await self._start_notify()

    async def _start_notify(self) -> None:
        if self._client is None or self._notify_started:
            return
        await self._client.start_notify(CHAR_RX, self._on_notify)
        self._notify_started = True

    def _client_disconnected(self, _client: BleakClientWithServiceCache) -> None:
        _LOGGER.debug("COJI disconnected")
        self._client = None
        self._notify_started = False
        for waiter in self._waiters.values():
            if not waiter.done():
                waiter.set_exception(ConnectionError("COJI disconnected"))

    def _arm_idle(self) -> None:
        """Disconnect after the session has been quiet."""
        self._cancel_idle()
        session = self._session
        loop = asyncio.get_running_loop()
        self._idle_handle = loop.call_later(
            SESSION_IDLE_SECONDS,
            lambda: asyncio.create_task(self._disconnect_if_idle(session)),
        )

    def _cancel_idle(self) -> None:
        if self._idle_handle is not None:
            self._idle_handle.cancel()
            self._idle_handle = None

    async def _disconnect_if_idle(self, session: int) -> None:
        async with self._lock:
            if session != self._session:
                return
            self._idle_handle = None
            _LOGGER.info("COJI %s session idle, disconnecting", self.address)
            await self._disconnect()

    async def _disconnect(self) -> None:
        client = self._client
        self._client = None
        self._notify_started = False
        if client is None:
            return
        try:
            if client.is_connected:
                await client.disconnect()
        except BleakConnectionError:
            _LOGGER.debug("COJI disconnect failed", exc_info=True)

    async def _write(self, payload: bytes) -> None:
        if self._client is None or not self._client.is_connected:
            raise ConnectionError("COJI is not connected")
        for offset in range(0, len(payload), NOTIFY_CHUNK):
            chunk = payload[offset : offset + NOTIFY_CHUNK]
            await self._client.write_gatt_char(CHAR_TX, chunk, response=False)
            if offset + NOTIFY_CHUNK < len(payload):
                await asyncio.sleep(0.025)

    async def _request(self, command: int, extra: bytes = b"") -> bytes:
        loop = asyncio.get_running_loop()
        waiter: asyncio.Future[bytes] = loop.create_future()
        self._waiters[command] = waiter
        try:
            await self._write(bytes((command,)) + extra)
            return await asyncio.wait_for(waiter, COMMAND_TIMEOUT)
        finally:
            self._waiters.pop(command, None)

    def _on_notify(self, _characteristic: int, data: bytearray) -> None:
        for command, payload in feed_rx(self._rx_buffer, bytes(data)):
            self._apply(command, payload)
            waiter = self._waiters.get(command)
            if waiter is not None and not waiter.done():
                waiter.set_result(payload)

    def _apply(self, command: int, payload: bytes) -> None:
        changed = False
        if command == CMD_BATTERY and len(payload) >= 2:
            self.state.battery_voltage = round(battery_voltage(payload[:2]), 3)
            changed = True
        elif command == CMD_GET_VOLUME and payload:
            self.state.volume = volume_percent(payload[0])
            changed = True
        elif command == CMD_GET_BACKLIGHT and payload:
            self.state.backlight = (payload[0] & 0xFF) == 1
            changed = True
        elif command == CMD_GET_CHEST and len(payload) >= 3:
            self.state.chest_red = (payload[0] & 0xFF) == 255
            self.state.chest_green = (payload[1] & 0xFF) == 255
            self.state.chest_blue = (payload[2] & 0xFF) == 255
            changed = True
        elif command == CMD_GET_FIRMWARE and payload:
            self.state.firmware = format_firmware(payload)
            changed = True
        elif command == CMD_BUTTON and len(payload) >= 3:
            self.state.left_button = (payload[0] & 0xFF) == 1
            self.state.center_button = (payload[1] & 0xFF) == 1
            self.state.right_button = (payload[2] & 0xFF) == 1
            changed = True
        elif command == CMD_ACCEL and payload:
            flags = parse_attitude(payload)
            self.state.attitude_flags = flags
            self.state.attitude = attitude_summary(flags)
            changed = True
        if changed:
            self._emit()

    def _emit(self) -> None:
        for listener in list(self._listeners):
            listener(self.state)


def _catalog_key(catalog: dict[str, str], name_or_path: str) -> str | None:
    key = name_or_path.strip()
    if key in catalog:
        return key
    lowered = key.lower()
    for name in catalog:
        if name.lower() == lowered:
            return name
    return None
