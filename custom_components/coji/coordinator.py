"""COJI data update coordinator."""

from __future__ import annotations

import logging
from datetime import timedelta

from homeassistant.components.bluetooth import (
    async_address_present,
    async_ble_device_from_address,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.device_registry import CONNECTION_BLUETOOTH, DeviceInfo
from homeassistant.helpers.update_coordinator import (
    CoordinatorEntity,
    DataUpdateCoordinator,
    UpdateFailed,
)

from .api import CojiClient, CojiState
from .const import DOMAIN, MANUFACTURER, MODEL

_LOGGER = logging.getLogger(__name__)


class CojiUpdateCoordinator(DataUpdateCoordinator[dict]):
    """Poll battery, volume, and LED state."""

    def __init__(
        self,
        hass: HomeAssistant,
        client: CojiClient,
        unique_id: str | None,
        config_entry: ConfigEntry | None = None,
    ) -> None:
        """Initialize the coordinator."""
        super().__init__(
            hass,
            _LOGGER,
            config_entry=config_entry,
            name=DOMAIN,
            update_interval=timedelta(seconds=180),
        )
        self.client = client
        self.unique_id = unique_id
        client.add_listener(self._on_client_state)

    def _on_client_state(self, state: CojiState) -> None:
        """Push notification updates onto the Home Assistant loop.

        The first refresh fills ``data`` itself, so listeners stay quiet
        until that snapshot exists.
        """
        if self.data is None:
            return
        data = state.as_dict()
        self.hass.loop.call_soon_threadsafe(self.async_set_updated_data, data)

    async def _async_update_data(self) -> dict:
        address = self.client.address
        if not async_address_present(self.hass, address, True):
            raise UpdateFailed(f"COJI {address} is not advertising")
        device = async_ble_device_from_address(self.hass, address, True)
        if device is None:
            raise UpdateFailed(f"COJI {address} is not in range")
        self.client.device = device
        try:
            state = await self.client.refresh()
        except (TimeoutError, ConnectionError) as err:
            raise UpdateFailed(str(err)) from err
        return state.as_dict()


class CojiEntity(CoordinatorEntity[CojiUpdateCoordinator]):
    """Base entity for one COJI."""

    _attr_has_entity_name = True

    def __init__(self, coordinator: CojiUpdateCoordinator) -> None:
        """Initialize the entity."""
        super().__init__(coordinator)
        self._client = coordinator.client

    @property
    def device_info(self) -> DeviceInfo:
        """Return device registry info."""
        assert self.coordinator.unique_id
        firmware = (self.coordinator.data or {}).get("firmware")
        return DeviceInfo(
            connections={(CONNECTION_BLUETOOTH, self._client.address)},
            identifiers={(DOMAIN, self.coordinator.unique_id)},
            manufacturer=MANUFACTURER,
            model=MODEL,
            name=self._client.name,
            sw_version=firmware,
        )

    @callback
    def _publish(self) -> None:
        self.coordinator.async_set_updated_data(self._client.state.as_dict())
