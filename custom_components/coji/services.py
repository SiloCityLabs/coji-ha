"""COJI services."""

from __future__ import annotations

import logging

import voluptuous as vol
from homeassistant.core import HomeAssistant, ServiceCall, callback
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.service import async_extract_config_entry_ids

from .const import (
    ANIMATIONS,
    DOMAIN,
    DRIVE_BURST_SECONDS,
    IMAGE_TEMPLATES,
    IMAGES,
    SERVICE_DRIVE,
    SERVICE_PLAY_ANIMATION,
    SERVICE_PLAY_SOUND,
    SERVICE_SHOW_IMAGE,
    SERVICE_STOP,
    SOUNDS,
)
from .coordinator import CojiUpdateCoordinator

_LOGGER = logging.getLogger(__name__)

DRIVE_SCHEMA = vol.Schema(
    {
        vol.Required("direction"): vol.In(["forward", "backward", "left", "right"]),
        vol.Optional("speed", default=1.0): vol.All(
            vol.Coerce(float), vol.Range(min=0, max=1)
        ),
        vol.Optional("seconds", default=DRIVE_BURST_SECONDS): vol.All(
            vol.Coerce(float), vol.Range(min=0.008, max=2.04)
        ),
    },
    extra=vol.ALLOW_EXTRA,
)

PLAY_SOUND_SCHEMA = vol.Schema(
    {
        vol.Required("sound"): cv.string,
    },
    extra=vol.ALLOW_EXTRA,
)

PLAY_ANIMATION_SCHEMA = vol.Schema(
    {
        vol.Required("animation"): cv.string,
        vol.Optional("sound", default=True): cv.boolean,
    },
    extra=vol.ALLOW_EXTRA,
)

SHOW_IMAGE_SCHEMA = vol.Schema(
    {
        vol.Required("image"): cv.string,
        vol.Optional("template", default="none"): vol.In(list(IMAGE_TEMPLATES)),
        vol.Optional("duration", default=0): vol.All(
            vol.Coerce(int), vol.Range(min=0, max=30)
        ),
    },
    extra=vol.ALLOW_EXTRA,
)


async def _coordinators(
    hass: HomeAssistant, call: ServiceCall
) -> list[CojiUpdateCoordinator]:
    entry_ids = await async_extract_config_entry_ids(hass, call)
    found: list[CojiUpdateCoordinator] = []
    for entry_id in entry_ids:
        entry = hass.config_entries.async_get_entry(entry_id)
        if entry and entry.domain == DOMAIN and entry.runtime_data is not None:
            found.append(entry.runtime_data)
    return found


@callback
def async_setup_services(hass: HomeAssistant) -> None:
    """Register domain services once."""
    if hass.services.has_service(DOMAIN, SERVICE_DRIVE):
        return

    async def handle_drive(call: ServiceCall) -> None:
        for coordinator in await _coordinators(hass, call):
            await coordinator.client.drive(
                call.data["direction"],
                float(call.data["speed"]),
                float(call.data["seconds"]),
            )

    async def handle_sound(call: ServiceCall) -> None:
        for coordinator in await _coordinators(hass, call):
            await coordinator.client.play_sound(call.data["sound"])
            coordinator.async_set_updated_data(coordinator.client.state.as_dict())

    async def handle_animation(call: ServiceCall) -> None:
        for coordinator in await _coordinators(hass, call):
            await coordinator.client.play_animation(
                call.data["animation"],
                sound=bool(call.data["sound"]),
            )
            coordinator.async_set_updated_data(coordinator.client.state.as_dict())

    async def handle_image(call: ServiceCall) -> None:
        for coordinator in await _coordinators(hass, call):
            await coordinator.client.show_image(
                call.data["image"],
                template=call.data["template"],
                duration=int(call.data["duration"]),
            )
            coordinator.async_set_updated_data(coordinator.client.state.as_dict())

    async def handle_stop(call: ServiceCall) -> None:
        for coordinator in await _coordinators(hass, call):
            await coordinator.client.stop()

    hass.services.async_register(
        DOMAIN, SERVICE_DRIVE, handle_drive, schema=DRIVE_SCHEMA
    )
    hass.services.async_register(
        DOMAIN, SERVICE_PLAY_SOUND, handle_sound, schema=PLAY_SOUND_SCHEMA
    )
    hass.services.async_register(
        DOMAIN,
        SERVICE_PLAY_ANIMATION,
        handle_animation,
        schema=PLAY_ANIMATION_SCHEMA,
    )
    hass.services.async_register(
        DOMAIN, SERVICE_SHOW_IMAGE, handle_image, schema=SHOW_IMAGE_SCHEMA
    )
    hass.services.async_register(DOMAIN, SERVICE_STOP, handle_stop)

    _LOGGER.debug(
        "COJI catalogs: %s sounds, %s animations, %s images",
        len(SOUNDS),
        len(ANIMATIONS),
        len(IMAGES),
    )


@callback
def async_unload_services(hass: HomeAssistant) -> None:
    """Remove services after the last entry unloads."""
    if hass.config_entries.async_entries(DOMAIN):
        return
    for service in (
        SERVICE_DRIVE,
        SERVICE_PLAY_SOUND,
        SERVICE_PLAY_ANIMATION,
        SERVICE_SHOW_IMAGE,
        SERVICE_STOP,
    ):
        if hass.services.has_service(DOMAIN, service):
            hass.services.async_remove(DOMAIN, service)
