"""COJI head-button sensors."""

from __future__ import annotations

from homeassistant.components.binary_sensor import BinarySensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .coordinator import CojiEntity, CojiUpdateCoordinator

_BUTTONS = (
    ("left_button", "left_button"),
    ("center_button", "center_button"),
    ("right_button", "right_button"),
)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up head-button sensors."""
    coordinator: CojiUpdateCoordinator = config_entry.runtime_data
    async_add_entities(
        CojiHeadButton(coordinator, key, translation_key)
        for key, translation_key in _BUTTONS
    )


class CojiHeadButton(CojiEntity, BinarySensorEntity):
    """One of the three buttons on COJI's head.

    The robot only reports these while Home Assistant is connected, which
    is during a poll or a command.
    """

    _attr_icon = "mdi:gesture-tap-button"

    def __init__(
        self,
        coordinator: CojiUpdateCoordinator,
        key: str,
        translation_key: str,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._key = key
        self._attr_unique_id = f"{coordinator.unique_id}_{key}"
        self._attr_translation_key = translation_key

    @property
    def is_on(self) -> bool | None:
        """Return the last reported press state."""
        return (self.coordinator.data or {}).get(self._key)
