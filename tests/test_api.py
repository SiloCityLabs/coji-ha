"""Tests for the COJI BLE client."""

import asyncio
import time
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from bleak.backends.device import BLEDevice

from custom_components.coji.api import CojiClient
from custom_components.coji.const import CHAR_RX, CHAR_TX, CMD_BATTERY, CMD_GET_VOLUME


@pytest.fixture
def device() -> BLEDevice:
    """Fake BLE peripheral."""
    ble = MagicMock(spec=BLEDevice)
    ble.address = "AA:BB:CC:DD:EE:FF"
    ble.name = "COJI"
    return ble


def _client() -> MagicMock:
    client = MagicMock()
    client.is_connected = True
    client.start_notify = AsyncMock()
    client.write_gatt_char = AsyncMock()
    client.disconnect = AsyncMock()
    return client


@pytest.mark.asyncio
async def test_refresh_parses_ascii_replies(device: BLEDevice):
    """Volume and battery notifications update state."""
    api = CojiClient(device)
    gatt = _client()

    async def write(_uuid, payload, response=False):
        assert response is False
        assert _uuid == CHAR_TX
        command = payload[0]
        if command == CMD_GET_VOLUME:
            api._on_notify(0, bytearray(b"2219"))
        elif command == CMD_BATTERY:
            api._on_notify(0, bytearray(b"A001F4"))
        elif command == 0x25:
            api._on_notify(0, bytearray(b"2501"))
        elif command == 0xB0:
            api._on_notify(0, bytearray(b"B0FF00FF"))
        elif command == 0x14:
            api._on_notify(0, bytearray(b"140E021B07"))

    gatt.write_gatt_char.side_effect = write

    with patch(
        "custom_components.coji.api.establish_connection",
        new_callable=AsyncMock,
        return_value=gatt,
    ):
        state = await api.refresh()

    gatt.start_notify.assert_awaited_once()
    assert gatt.start_notify.await_args.args[0] == CHAR_RX
    assert state.volume == 50
    assert state.backlight is True
    assert state.chest_red is True
    assert state.chest_green is False
    assert state.chest_blue is True
    assert state.firmware == "142277"
    assert state.battery_voltage == round(500 * 0.00322 * 3, 3)
    gatt.disconnect.assert_not_awaited()
    await api.async_shutdown()
    gatt.disconnect.assert_awaited()


@pytest.mark.asyncio
async def test_drive_writes_timed_burst(device: BLEDevice):
    """A drive button sends one raw packet and does not wait for a reply."""
    api = CojiClient(device)
    gatt = _client()

    with patch(
        "custom_components.coji.api.establish_connection",
        new_callable=AsyncMock,
        return_value=gatt,
    ):
        await api.drive("forward", 1.0, 0.16)

    gatt.write_gatt_char.assert_awaited_once_with(
        CHAR_TX, bytes((0x71, 100, 20)), response=False
    )
    await api.async_shutdown()


@pytest.mark.asyncio
async def test_refresh_fails_when_nothing_answers(device: BLEDevice):
    """A silent robot surfaces as a timeout."""
    api = CojiClient(device)
    gatt = _client()

    with (
        patch(
            "custom_components.coji.api.establish_connection",
            new_callable=AsyncMock,
            return_value=gatt,
        ),
        patch("custom_components.coji.api.COMMAND_TIMEOUT", 0.01),
        pytest.raises(TimeoutError),
    ):
        await api.refresh()
    gatt.write_gatt_char.assert_awaited_once()


@pytest.mark.asyncio
async def test_failed_connect_backs_off(device: BLEDevice):
    """A second command does not open another connection during cooldown."""
    api = CojiClient(device)
    api._backoff_until = time.monotonic() + 30

    with (
        patch(
            "custom_components.coji.api.establish_connection",
            new_callable=AsyncMock,
        ) as connect,
        pytest.raises(ConnectionError, match="cooling down"),
    ):
        await api.drive("forward")

    connect.assert_not_awaited()


@pytest.mark.asyncio
async def test_commands_queued_behind_a_slow_link_are_dropped(device: BLEDevice):
    """Presses that piled up while the robot was offline are not flushed later."""
    api = CojiClient(device)
    await api._lock.acquire()

    async def _release() -> None:
        await asyncio.sleep(0.05)
        api._lock.release()

    release = asyncio.create_task(_release())
    with (
        patch("custom_components.coji.api.STALE_AFTER_SECONDS", 0.01),
        patch(
            "custom_components.coji.api.establish_connection",
            new_callable=AsyncMock,
        ) as connect,
        pytest.raises(ConnectionError, match="busy"),
    ):
        await api.drive("forward")

    await release
    connect.assert_not_awaited()
