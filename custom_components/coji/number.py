"""COJI volume."""

from __future__ import annotations

from homeassistant.components.number import NumberEntity, NumberMode
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .coordinator import CojiEntity, CojiUpdateCoordinator


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the volume number."""
    coordinator: CojiUpdateCoordinator = config_entry.runtime_data
    async_add_entities([CojiVolumeNumber(coordinator)])


class CojiVolumeNumber(CojiEntity, NumberEntity):
    """Volume slider. The robot stores 0–50; this entity is 0–100."""

    _attr_native_min_value = 0
    _attr_native_max_value = 100
    _attr_native_step = 1
    _attr_mode = NumberMode.SLIDER
    _attr_icon = "mdi:volume-high"

    def __init__(self, coordinator: CojiUpdateCoordinator) -> None:
        """Initialize the number."""
        super().__init__(coordinator)
        self._attr_unique_id = f"{coordinator.unique_id}_volume"
        self._attr_translation_key = "volume"

    @property
    def native_value(self) -> float | None:
        """Return the last volume percent."""
        value = (self.coordinator.data or {}).get("volume")
        return None if value is None else float(value)

    async def async_set_native_value(self, value: float) -> None:
        """Write volume to the robot."""
        await self._client.set_volume(value)
        self._publish()
