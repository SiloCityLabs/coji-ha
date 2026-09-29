"""Tests for integration setup."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from homeassistant.config_entries import ConfigEntryState
from homeassistant.const import CONF_ADDRESS
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.coji import async_setup, async_setup_entry
from custom_components.coji.const import DOMAIN


@pytest.mark.asyncio
async def test_setup_requires_a_visible_radio(hass: HomeAssistant):
    """Setup waits when the robot is not in the Bluetooth stack yet."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        unique_id="aabbccddeeff",
        data={CONF_ADDRESS: "AA:BB:CC:DD:EE:FF"},
    )
    entry.add_to_hass(hass)
    with (
        patch(
            "custom_components.coji.bluetooth.async_ble_device_from_address",
            return_value=None,
        ),
        pytest.raises(ConfigEntryNotReady),
    ):
        await async_setup_entry(hass, entry)
    assert entry.state is not ConfigEntryState.LOADED


@pytest.mark.asyncio
async def test_setup_forwards_platforms(hass: HomeAssistant):
    """A successful first poll loads every platform."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        unique_id="aabbccddeeff",
        data={CONF_ADDRESS: "AA:BB:CC:DD:EE:FF"},
    )
    entry.add_to_hass(hass)
    ble = MagicMock()
    ble.address = "AA:BB:CC:DD:EE:FF"
    ble.name = "COJI"

    mock_client = MagicMock()
    mock_client.address = ble.address
    mock_client.name = "COJI"
    mock_client.state.as_dict.return_value = {"firmware": "2014-02-27 r7"}
    mock_client.refresh = AsyncMock(return_value=mock_client.state)
    mock_client.add_listener = MagicMock()

    with (
        patch(
            "custom_components.coji.bluetooth.async_ble_device_from_address",
            return_value=ble,
        ),
        patch(
            "custom_components.coji.CojiClient",
            return_value=mock_client,
        ),
        patch(
            "custom_components.coji.coordinator.async_ble_device_from_address",
            return_value=ble,
        ),
        patch(
            "custom_components.coji.coordinator.async_address_present",
            return_value=True,
        ),
        patch(
            "homeassistant.config_entries.ConfigEntries.async_forward_entry_setups",
            new_callable=AsyncMock,
        ) as forward,
    ):
        assert await async_setup_entry(hass, entry) is True

    forward.assert_awaited()
    assert entry.runtime_data.client is mock_client


@pytest.mark.asyncio
async def test_remote_card_is_registered_once(hass: HomeAssistant):
    """The Lovelace module is attached once, even if setup runs twice."""
    hass.http = MagicMock()
    hass.http.async_register_static_paths = AsyncMock()
    hass.http.register_view = MagicMock()
    with patch(
        "custom_components.coji.frontend._async_ensure_lovelace_resource",
        new_callable=AsyncMock,
    ) as ensure:
        assert await async_setup(hass, {}) is True
        assert await async_setup(hass, {}) is True

    hass.http.async_register_static_paths.assert_awaited_once()
    hass.http.register_view.assert_called_once()
    ensure.assert_awaited_once()
