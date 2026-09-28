"""COJI backlight."""

from __future__ import annotations

from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .coordinator import CojiEntity, CojiUpdateCoordinator


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the backlight switch."""
    coordinator: CojiUpdateCoordinator = config_entry.runtime_data
    async_add_entities([CojiBacklightSwitch(coordinator)])


class CojiBacklightSwitch(CojiEntity, SwitchEntity):
    """LCD backlight behind the face screen."""

    _attr_icon = "mdi:television-ambient-light"

    def __init__(self, coordinator: CojiUpdateCoordinator) -> None:
        """Initialize the switch."""
        super().__init__(coordinator)
        self._attr_unique_id = f"{coordinator.unique_id}_backlight"
        self._attr_translation_key = "backlight"

    @property
    def is_on(self) -> bool | None:
        """Return backlight state."""
        return (self.coordinator.data or {}).get("backlight")

    async def async_turn_on(self, **kwargs) -> None:
        """Turn the backlight on."""
        await self._client.set_backlight(True)
        self._publish()

    async def async_turn_off(self, **kwargs) -> None:
        """Turn the backlight off."""
        await self._client.set_backlight(False)
        self._publish()
