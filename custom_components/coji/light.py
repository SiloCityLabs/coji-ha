"""COJI chest LED."""

from __future__ import annotations

from typing import Any, ClassVar

from homeassistant.components.light import (
    ATTR_BRIGHTNESS,
    ATTR_RGB_COLOR,
    ColorMode,
    LightEntity,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .coordinator import CojiEntity, CojiUpdateCoordinator


def _channel(value: int) -> bool:
    return value >= 128


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the chest light."""
    coordinator: CojiUpdateCoordinator = config_entry.runtime_data
    async_add_entities([CojiChestLight(coordinator)])


class CojiChestLight(CojiEntity, LightEntity):
    """Chest LED. Each color is only on or off."""

    _attr_supported_color_modes: ClassVar[set[ColorMode]] = {ColorMode.RGB}
    _attr_color_mode = ColorMode.RGB
    _attr_icon = "mdi:led-on"

    def __init__(self, coordinator: CojiUpdateCoordinator) -> None:
        """Initialize the light."""
        super().__init__(coordinator)
        self._attr_unique_id = f"{coordinator.unique_id}_chest"
        self._attr_translation_key = "chest"

    @property
    def is_on(self) -> bool:
        """Return whether any channel is lit."""
        data = self.coordinator.data or {}
        return bool(
            data.get("chest_red") or data.get("chest_green") or data.get("chest_blue")
        )

    @property
    def rgb_color(self) -> tuple[int, int, int]:
        """Return 0 or 255 per channel."""
        data = self.coordinator.data or {}
        return (
            255 if data.get("chest_red") else 0,
            255 if data.get("chest_green") else 0,
            255 if data.get("chest_blue") else 0,
        )

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Snap RGB to the three on/off channels."""
        brightness = kwargs.get(ATTR_BRIGHTNESS)
        if brightness == 0:
            await self._client.set_chest(False, False, False)
            self._publish()
            return
        rgb = kwargs.get(ATTR_RGB_COLOR)
        if rgb is not None:
            red, green, blue = (_channel(int(channel)) for channel in rgb)
        elif not self.is_on:
            red = green = blue = True
        else:
            red, green, blue = (channel >= 128 for channel in self.rgb_color)
        await self._client.set_chest(red, green, blue)
        self._publish()

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn every chest channel off."""
        await self._client.set_chest(False, False, False)
        self._publish()
