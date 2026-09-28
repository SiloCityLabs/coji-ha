"""COJI sensors."""

from __future__ import annotations

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EntityCategory, UnitOfElectricPotential
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .coordinator import CojiEntity, CojiUpdateCoordinator


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up COJI sensors."""
    coordinator: CojiUpdateCoordinator = config_entry.runtime_data
    async_add_entities(
        [
            CojiBatterySensor(coordinator),
            CojiFirmwareSensor(coordinator),
            CojiAttitudeSensor(coordinator),
        ]
    )


class CojiBatterySensor(CojiEntity, SensorEntity):
    """Battery voltage from the robot's ADC."""

    _attr_device_class = SensorDeviceClass.VOLTAGE
    _attr_native_unit_of_measurement = UnitOfElectricPotential.VOLT
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_suggested_display_precision = 2
    _attr_icon = "mdi:battery"

    def __init__(self, coordinator: CojiUpdateCoordinator) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._attr_unique_id = f"{coordinator.unique_id}_battery"
        self._attr_translation_key = "battery"

    @property
    def native_value(self) -> float | None:
        """Return voltage."""
        value = (self.coordinator.data or {}).get("battery_voltage")
        return None if value is None else float(value)


class CojiFirmwareSensor(CojiEntity, SensorEntity):
    """Firmware date reported by command 0x14."""

    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_icon = "mdi:chip"

    def __init__(self, coordinator: CojiUpdateCoordinator) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._attr_unique_id = f"{coordinator.unique_id}_firmware"
        self._attr_translation_key = "firmware"

    @property
    def native_value(self) -> str | None:
        """Return the firmware string."""
        return (self.coordinator.data or {}).get("firmware")


class CojiAttitudeSensor(CojiEntity, SensorEntity):
    """Tilt, shake, and pickup flags."""

    _attr_icon = "mdi:axis-arrow"

    def __init__(self, coordinator: CojiUpdateCoordinator) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._attr_unique_id = f"{coordinator.unique_id}_attitude"
        self._attr_translation_key = "attitude"

    @property
    def native_value(self) -> str | None:
        """Return the winning attitude flag."""
        return (self.coordinator.data or {}).get("attitude")

    @property
    def extra_state_attributes(self) -> dict:
        """Expose each accelerometer flag."""
        return {
            "flags": (self.coordinator.data or {}).get("attitude_flags") or {},
        }
