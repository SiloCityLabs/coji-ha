"""COJI integration."""

from __future__ import annotations

import logging

from homeassistant.components import bluetooth
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_ADDRESS, Platform
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady

from .api import CojiClient
from .config_flow import format_unique_id
from .coordinator import CojiUpdateCoordinator
from .services import async_setup_services, async_unload_services

_LOGGER = logging.getLogger(__name__)

PLATFORMS = [
    Platform.BINARY_SENSOR,
    Platform.BUTTON,
    Platform.LIGHT,
    Platform.NUMBER,
    Platform.SELECT,
    Platform.SENSOR,
    Platform.SWITCH,
]

type CojiConfigEntry = ConfigEntry[CojiUpdateCoordinator]


async def async_setup_entry(hass: HomeAssistant, entry: CojiConfigEntry) -> bool:
    """Set up a COJI from a config entry."""
    address = entry.data[CONF_ADDRESS]
    ble_device = bluetooth.async_ble_device_from_address(hass, address.upper(), True)
    if ble_device is None:
        raise ConfigEntryNotReady(f"Could not find COJI with address {address}")

    client = CojiClient(ble_device)
    coordinator = CojiUpdateCoordinator(
        hass,
        client,
        entry.unique_id or format_unique_id(address),
        config_entry=entry,
    )
    await coordinator.async_config_entry_first_refresh()
    entry.runtime_data = coordinator
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    async_setup_services(hass)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: CojiConfigEntry) -> bool:
    """Unload a COJI config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        async_unload_services(hass)
    return unload_ok
