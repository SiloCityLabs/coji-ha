"""Fixtures for COJI tests."""

from unittest.mock import AsyncMock, patch

import pytest


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations):
    """Load the custom component under test."""
    return


@pytest.fixture(autouse=True)
def mock_bluez_setup():
    """Don't open a host Bluetooth socket while the bluetooth integration starts."""
    with patch(
        "habluetooth.channels.bluez.MGMTBluetoothCtl.setup",
        new_callable=AsyncMock,
    ):
        yield
