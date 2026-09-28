"""COJI buttons."""

from __future__ import annotations

from collections.abc import Awaitable, Callable

from homeassistant.components.button import ButtonEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DRIVE_BURST_SECONDS
from .coordinator import CojiEntity, CojiUpdateCoordinator


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up drive and power buttons."""
    coordinator: CojiUpdateCoordinator = config_entry.runtime_data
    async_add_entities(
        [
            CojiDriveButton(coordinator, "forward", "mdi:arrow-up-bold"),
            CojiDriveButton(coordinator, "backward", "mdi:arrow-down-bold"),
            CojiDriveButton(coordinator, "left", "mdi:arrow-left-bold"),
            CojiDriveButton(coordinator, "right", "mdi:arrow-right-bold"),
            CojiActionButton(
                coordinator,
                "stop",
                "mdi:stop",
                coordinator.client.stop,
            ),
            CojiActionButton(
                coordinator,
                "power_off",
                "mdi:power",
                coordinator.client.power_off,
                entity_category=EntityCategory.CONFIG,
            ),
        ]
    )


class CojiDriveButton(CojiEntity, ButtonEntity):
    """One timed drive burst at full speed."""

    def __init__(
        self,
        coordinator: CojiUpdateCoordinator,
        direction: str,
        icon: str,
    ) -> None:
        """Initialize the button."""
        super().__init__(coordinator)
        self._direction = direction
        self._attr_unique_id = f"{coordinator.unique_id}_drive_{direction}"
        self._attr_translation_key = f"drive_{direction}"
        self._attr_icon = icon

    async def async_press(self) -> None:
        """Drive for the SDK sample burst (0.16s)."""
        await self._client.drive(self._direction, 1.0, DRIVE_BURST_SECONDS)


class CojiActionButton(CojiEntity, ButtonEntity):
    """A single robot command."""

    def __init__(
        self,
        coordinator: CojiUpdateCoordinator,
        key: str,
        icon: str,
        action: Callable[[], Awaitable[None]],
        entity_category: EntityCategory | None = None,
    ) -> None:
        """Initialize the button."""
        super().__init__(coordinator)
        self._action = action
        self._attr_unique_id = f"{coordinator.unique_id}_{key}"
        self._attr_translation_key = key
        self._attr_icon = icon
        self._attr_entity_category = entity_category

    async def async_press(self) -> None:
        """Run the command."""
        await self._action()
