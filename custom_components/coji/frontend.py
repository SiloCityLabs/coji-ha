"""Serve the COJI remote card with the integration."""

from __future__ import annotations

import json
import logging
from pathlib import Path

from homeassistant.components.frontend import add_extra_js_url
from homeassistant.components.http import StaticPathConfig
from homeassistant.core import HomeAssistant

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

_REGISTERED = "frontend_registered"


def _card_version() -> str:
    manifest = Path(__file__).parent / "manifest.json"
    return json.loads(manifest.read_text(encoding="utf-8"))["version"]


async def async_register_card(hass: HomeAssistant) -> None:
    """Register the Lovelace module once per process."""
    bucket = hass.data.setdefault(DOMAIN, {})
    if bucket.get(_REGISTERED):
        return
    root = Path(__file__).parent / "www"
    await hass.http.async_register_static_paths(
        [StaticPathConfig("/coji_remote", str(root), False)]
    )
    url = f"/coji_remote/coji-remote-card.js?v={_card_version()}"
    try:
        add_extra_js_url(hass, url)
    except KeyError:
        _LOGGER.debug("Frontend is not loaded yet; COJI remote card was not registered")
        return
    bucket[_REGISTERED] = True
