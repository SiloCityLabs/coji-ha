"""Tests for the COJI config flow."""

from unittest.mock import patch

import pytest
from homeassistant import config_entries
from homeassistant.components.bluetooth import BluetoothServiceInfoBleak
from homeassistant.const import CONF_ADDRESS, CONF_NAME
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType

from custom_components.coji.config_flow import format_unique_id
from custom_components.coji.const import DOMAIN, MANUFACTURER_ID


def _info(
    name: str = "COJI",
    manufacturer: int | None = MANUFACTURER_ID,
) -> BluetoothServiceInfoBleak:
    return BluetoothServiceInfoBleak(
        name=name,
        address="AA:BB:CC:DD:EE:FF",
        rssi=-50,
        manufacturer_data={} if manufacturer is None else {manufacturer: b"\x00"},
        service_data={},
        service_uuids=[],
        source="local",
        device=None,
        advertisement=None,
        connectable=True,
        time=0,
        tx_power=None,
    )


def test_format_unique_id():
    assert format_unique_id("AA:BB:CC:DD:EE:FF") == "aabbccddeeff"


@pytest.mark.asyncio
async def test_bluetooth_confirm_creates_entry(hass: HomeAssistant):
    """Discovery asks for confirmation, then stores the address."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": config_entries.SOURCE_BLUETOOTH},
        data=_info(),
    )
    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "bluetooth_confirm"

    result = await hass.config_entries.flow.async_configure(result["flow_id"], {})
    assert result["type"] == FlowResultType.CREATE_ENTRY
    assert result["title"] == "COJI"
    assert result["data"][CONF_ADDRESS] == "AA:BB:CC:DD:EE:FF"
    assert result["data"][CONF_NAME] == "COJI"


@pytest.mark.asyncio
async def test_bluetooth_ignores_other_robots(hass: HomeAssistant):
    """MiP advertisements are not a COJI."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": config_entries.SOURCE_BLUETOOTH},
        data=_info(name="Mip-1", manufacturer=0x0500),
    )
    assert result["type"] == FlowResultType.ABORT
    assert result["reason"] == "not_coji"


@pytest.mark.asyncio
async def test_user_step_lists_discovered_coji(hass: HomeAssistant):
    """The manual flow offers robots already seen by Home Assistant."""
    with patch(
        "custom_components.coji.config_flow.async_discovered_service_info",
        return_value=[_info(name="COJI-9")],
    ):
        result = await hass.config_entries.flow.async_init(
            DOMAIN,
            context={"source": config_entries.SOURCE_USER},
        )
        assert result["type"] == FlowResultType.FORM
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {CONF_ADDRESS: "AA:BB:CC:DD:EE:FF"},
        )
    assert result["type"] == FlowResultType.CREATE_ENTRY
    assert result["data"][CONF_NAME] == "COJI-9"


@pytest.mark.asyncio
async def test_user_step_aborts_when_nothing_is_nearby(hass: HomeAssistant):
    with patch(
        "custom_components.coji.config_flow.async_discovered_service_info",
        return_value=[],
    ):
        result = await hass.config_entries.flow.async_init(
            DOMAIN,
            context={"source": config_entries.SOURCE_USER},
        )
    assert result["type"] == FlowResultType.ABORT
    assert result["reason"] == "no_devices_found"
