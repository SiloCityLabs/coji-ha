"""COJI config flow."""

from __future__ import annotations

from typing import Any

import voluptuous as vol
from homeassistant.components.bluetooth import (
    BluetoothServiceInfoBleak,
    async_discovered_service_info,
)
from homeassistant.config_entries import ConfigFlow, ConfigFlowResult
from homeassistant.const import CONF_ADDRESS, CONF_NAME

from .const import DOMAIN
from .protocol import is_coji


def format_unique_id(address: str) -> str:
    """Format a Bluetooth address as a unique id."""
    return address.replace(":", "").replace("-", "").lower()


class CojiConfigFlow(ConfigFlow, domain=DOMAIN):
    """Set up a COJI from a Bluetooth advertisement."""

    VERSION = 1

    def __init__(self) -> None:
        """Initialize the flow."""
        self._discovery: BluetoothServiceInfoBleak | None = None

    async def async_step_bluetooth(
        self, discovery_info: BluetoothServiceInfoBleak
    ) -> ConfigFlowResult:
        """Handle a discovered advertisement."""
        if not is_coji(discovery_info.name, discovery_info.manufacturer_data):
            return self.async_abort(reason="not_coji")

        await self.async_set_unique_id(format_unique_id(discovery_info.address))
        self._abort_if_unique_id_configured()
        self._discovery = discovery_info
        name = discovery_info.name or "COJI"
        self.context["title_placeholders"] = {"name": name}
        return await self.async_step_bluetooth_confirm()

    async def async_step_bluetooth_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Confirm the discovered robot."""
        assert self._discovery is not None
        if user_input is not None:
            return self._create(self._discovery)

        self._set_confirm_only()
        return self.async_show_form(
            step_id="bluetooth_confirm",
            description_placeholders={
                "name": self._discovery.name or "COJI",
            },
        )

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Let the user pick a robot Home Assistant already sees."""
        if user_input is not None:
            address = user_input[CONF_ADDRESS]
            await self.async_set_unique_id(format_unique_id(address))
            self._abort_if_unique_id_configured()
            discovery = self._user_devices()[address]
            return self._create(discovery)

        devices = self._user_devices()
        if not devices:
            return self.async_abort(reason="no_devices_found")

        schema = vol.Schema(
            {
                vol.Required(CONF_ADDRESS): vol.In(
                    {
                        address: f"{info.name or 'COJI'} ({address})"
                        for address, info in devices.items()
                    }
                )
            }
        )
        return self.async_show_form(step_id="user", data_schema=schema)

    def _user_devices(self) -> dict[str, BluetoothServiceInfoBleak]:
        current = self._async_current_ids()
        found: dict[str, BluetoothServiceInfoBleak] = {}
        for info in async_discovered_service_info(self.hass):
            unique = format_unique_id(info.address)
            if unique in current or info.address in found:
                continue
            if is_coji(info.name, info.manufacturer_data):
                found[info.address] = info
        return found

    def _create(self, info: BluetoothServiceInfoBleak) -> ConfigFlowResult:
        name = info.name or "COJI"
        return self.async_create_entry(
            title=name,
            data={CONF_ADDRESS: info.address, CONF_NAME: name},
        )
