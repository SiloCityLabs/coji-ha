"""COJI sound, animation, and image selects."""

from __future__ import annotations

from collections.abc import Awaitable, Callable

from homeassistant.components.select import SelectEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import ANIMATIONS, IMAGES, SOUNDS
from .coordinator import CojiEntity, CojiUpdateCoordinator


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up clip selects. Choosing an option plays it."""
    coordinator: CojiUpdateCoordinator = config_entry.runtime_data
    async_add_entities(
        [
            CojiClipSelect(
                coordinator,
                "sound",
                list(SOUNDS),
                "mdi:music-note",
                lambda option: coordinator.client.play_sound(option),
            ),
            CojiClipSelect(
                coordinator,
                "animation",
                list(ANIMATIONS),
                "mdi:animation-play",
                lambda option: coordinator.client.play_animation(option),
            ),
            CojiClipSelect(
                coordinator,
                "image",
                list(IMAGES),
                "mdi:image",
                lambda option: coordinator.client.show_image(option),
            ),
        ]
    )


class CojiClipSelect(CojiEntity, SelectEntity):
    """Select that sends the matching on-device file."""

    def __init__(
        self,
        coordinator: CojiUpdateCoordinator,
        key: str,
        options: list[str],
        icon: str,
        play: Callable[[str], Awaitable[None]],
    ) -> None:
        """Initialize the select."""
        super().__init__(coordinator)
        self._key = key
        self._play = play
        self._attr_options = options
        self._attr_unique_id = f"{coordinator.unique_id}_{key}"
        self._attr_translation_key = key
        self._attr_icon = icon

    @property
    def current_option(self) -> str | None:
        """Return the last clip sent from Home Assistant."""
        return (self.coordinator.data or {}).get(self._key)

    async def async_select_option(self, option: str) -> None:
        """Play the selected clip."""
        await self._play(option)
        self._publish()
