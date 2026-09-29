"""Serve the COJI remote card with the integration."""

from __future__ import annotations

import hashlib
import json
import logging
from pathlib import Path
from typing import Any

from aiohttp import web
from homeassistant.components.http import HomeAssistantView, StaticPathConfig
from homeassistant.const import EVENT_HOMEASSISTANT_STARTED
from homeassistant.core import HomeAssistant

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

_REGISTERED = "frontend_registered"
_URL_BASE = "/coji_remote"
_CARD_FILENAME = "coji-remote-card.js"
_CARD_PATH = f"{_URL_BASE}/{_CARD_FILENAME}"
_STATIC_DIR = Path(__file__).parent / "www"
_CARD_FILE = _STATIC_DIR / _CARD_FILENAME
_MANIFEST_FILE = Path(__file__).parent / "manifest.json"
_RESOURCE_MARKERS = (_CARD_PATH, "/coji_remote/")
_VERSION = json.loads(_MANIFEST_FILE.read_text(encoding="utf-8"))["version"]


def _content_hash(body: str) -> str:
    return hashlib.sha256(body.encode("utf-8")).hexdigest()[:12]


def _resource_url(body: str) -> str:
    return f"{_CARD_PATH}?v={_VERSION}&h={_content_hash(body)}"


class CojiRemoteCardView(HomeAssistantView):
    """Serve the card JS with explicit UTF-8."""

    url = _CARD_PATH
    name = f"{DOMAIN}:remote_card"
    requires_auth = False
    cors_allowed = True

    async def get(self, request: web.Request) -> web.Response:
        body = await request.app["hass"].async_add_executor_job(
            _CARD_FILE.read_text, "utf-8"
        )
        return web.Response(
            text=body,
            content_type="text/javascript",
            charset="utf-8",
            headers={"Cache-Control": "no-cache, must-revalidate"},
        )


async def async_register_card(hass: HomeAssistant) -> None:
    """Register the Lovelace module once per process."""
    bucket = hass.data.setdefault(DOMAIN, {})
    if bucket.get(_REGISTERED):
        return

    await hass.http.async_register_static_paths(
        [StaticPathConfig(_URL_BASE, str(_STATIC_DIR), False)]
    )
    hass.http.register_view(CojiRemoteCardView)

    async def _on_started(_event: Any) -> None:
        await _async_ensure_lovelace_resource(hass)

    hass.bus.async_listen_once(EVENT_HOMEASSISTANT_STARTED, _on_started)
    await _async_ensure_lovelace_resource(hass)
    bucket[_REGISTERED] = True
    _LOGGER.info("Registered COJI remote card at %s", _CARD_PATH)


async def _async_ensure_lovelace_resource(hass: HomeAssistant) -> None:
    """Add or refresh the module resource in Lovelace storage mode."""
    try:
        lovelace = hass.data.get("lovelace")
        if lovelace is None:
            return
        resources = getattr(lovelace, "resources", None)
        if resources is None and isinstance(lovelace, dict):
            resources = lovelace.get("resources")
        if resources is None:
            return
        if hasattr(resources, "async_load"):
            await resources.async_load()
        items = (
            list(resources.async_items()) if hasattr(resources, "async_items") else []
        )
        body = await hass.async_add_executor_job(_CARD_FILE.read_text, "utf-8")
        preferred = _resource_url(body)
        related = [
            item
            for item in items
            if any(marker in item.get("url", "") for marker in _RESOURCE_MARKERS)
        ]
        if not related:
            await resources.async_create_item(
                {"res_type": "module", "url": preferred}
            )
            _LOGGER.info("Added Lovelace resource %s", preferred)
            return
        primary = related[0]
        if primary.get("url") != preferred:
            await resources.async_update_item(
                primary["id"], {"res_type": "module", "url": preferred}
            )
        for extra in related[1:]:
            await resources.async_delete_item(extra["id"])
    except Exception:
        _LOGGER.exception("Could not register the COJI Lovelace resource")
