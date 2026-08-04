"""Support for NGBS iCON Modbus TCP Thermostats."""
from __future__ import annotations

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    UnitOfTemperature,
    PERCENTAGE,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.typing import ConfigType, DiscoveryInfoType

from datetime import timedelta
from .const import DOMAIN, DEVICE_INFO
from .lib.ngbs import NGBSController

SCAN_INTERVAL = timedelta(seconds=5)


async def async_setup_platform(
    hass: HomeAssistant,
    config: ConfigType,
    async_add_entities: AddEntitiesCallback,
    discovery_info: DiscoveryInfoType | None = None,
) -> None:
    pass


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Set up NGBS iCON climate based on config_entry."""
    ngbs_controller: NGBSController = hass.data["ngbs"].get(entry.entry_id)
    async_add_entities(
        [
            NGBSSensor(
                SensorDeviceClass.TEMPERATURE,
                "current_temperature_" + thermostat.get_unique_id(),
                thermostat.get_current_temperature,
                thermostat.update,
            )
            for thermostat in ngbs_controller.get_thermostats()
        ],
        update_before_add=True,
    )
    async_add_entities(
        [
            NGBSSensor(
                SensorDeviceClass.TEMPERATURE,
                "target_temperature_" + thermostat.get_unique_id(),
                thermostat.get_target_temperature,
                thermostat.update,
            )
            for thermostat in ngbs_controller.get_thermostats()
        ],
        update_before_add=True,
    )
    async_add_entities(
        [
            NGBSSensor(
                SensorDeviceClass.HUMIDITY,
                "humidity_" + thermostat.get_unique_id(),
                thermostat.get_humidity,
                thermostat.update,
            )
            for thermostat in ngbs_controller.get_thermostats()
        ],
        update_before_add=True,
    )
    async_add_entities(
        [
            NGBSSensor(
                SensorDeviceClass.TEMPERATURE,
                "water_temperature_ngbs",
                ngbs_controller.get_water_temperature,
                ngbs_controller.update,
            )
        ],
        update_before_add=True,
    )


class NGBSSensor(SensorEntity):
    def __init__(
        self,
        device_class: SensorDeviceClass,
        unique_id,
        value_callback,
        update_callback,
    ):
        self._attr_name = unique_id
        self._attr_unique_id = unique_id
        self._attr_device_class = device_class

        if device_class == SensorDeviceClass.TEMPERATURE:
            self._attr_native_unit_of_measurement = UnitOfTemperature.CELSIUS
        elif device_class == SensorDeviceClass.HUMIDITY:
            self._attr_native_unit_of_measurement = PERCENTAGE
        self._attr_state_class = SensorStateClass.MEASUREMENT

        self._attr_device_info = DEVICE_INFO
        self.entity_id = f"{DOMAIN}.{self._attr_unique_id}"

        self._value_callback = value_callback
        self._update_callback = update_callback

    async def async_update(self):
        """Update device state."""
        await self._update_callback()
        self._attr_native_value = self._value_callback()
        self.async_write_ha_state()
