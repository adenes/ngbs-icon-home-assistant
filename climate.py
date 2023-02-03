"""Support for NGBS iCON Modbus TCP Thermostats."""
from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol
from homeassistant.components.climate import PLATFORM_SCHEMA, ClimateEntity
from homeassistant.components.climate.const import (
    PRESET_COMFORT,
    PRESET_ECO,
    ClimateEntityFeature,
    HVACAction,
    HVACMode,
)
from homeassistant.components.sensor import SensorEntity
from homeassistant.components.sensor import (
    PLATFORM_SCHEMA,
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)


from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    ATTR_TEMPERATURE,
    CONF_HOST,
    CONF_PORT,
    PRECISION_HALVES,
    TEMP_CELSIUS,
    UnitOfTemperature,
)
from homeassistant.core import HomeAssistant
import homeassistant.helpers.config_validation as cv
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.typing import ConfigType, DiscoveryInfoType

from .const import DOMAIN, DEVICE_INFO
from .lib.ngbs import NGBSThermostat

_LOGGER = logging.getLogger(__name__)

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend(
    {
        vol.Required(CONF_HOST, default="192.168.0.104"): cv.string,
        vol.Required(CONF_PORT, default=502): cv.port,
    }
)

HVAC_MODE_TO_HVAC_ACTION = {
    HVACMode.COOL: HVACAction.COOLING,
    HVACMode.HEAT: HVACAction.HEATING,
}


async def async_setup_platform(
    hass: HomeAssistant,
    config: ConfigType,
    async_add_entities: AddEntitiesCallback,
    discovery_info: DiscoveryInfoType | None = None,
) -> None:
    """Old way of setting up the Daikin HVAC platform.

    Can only be called when a user accidentally mentions the platform in their
    config. But even in that case it would have been ignored.
    """


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Set up NGBS iCON climate based on config_entry."""
    ngbs_controller = hass.data["ngbs"].get(entry.entry_id)
    async_add_entities(
        [NGBSClimate(thermostat) for thermostat in ngbs_controller.get_thermostats()],
        update_before_add=True,
    )


class NGBSClimate(ClimateEntity):
    """NGBSClimate Entity."""

    _attr_hvac_modes = [HVACMode.HEAT, HVACMode.COOL]
    _attr_hvac_mode = HVACMode.HEAT
    _attr_max_temp = 30
    _attr_min_temp = 5
    _attr_supported_features = (
        ClimateEntityFeature.TARGET_TEMPERATURE | ClimateEntityFeature.PRESET_MODE
    )

    _attr_target_temperature_step = PRECISION_HALVES
    _attr_temperature_unit = TEMP_CELSIUS

    _attr_preset_modes = [PRESET_COMFORT, PRESET_ECO]
    _attr_preset_mode = PRESET_COMFORT

    def __init__(self, thermostat: NGBSThermostat) -> None:
        """Initialize the climate device."""

        self._thermostat = thermostat
        self._attr_unique_id = thermostat.get_unique_id()
        self._attr_device_info = DEVICE_INFO
        self.entity_id = f"{DOMAIN}.{self._attr_unique_id}"

    @property
    def name(self):
        """Get the name."""
        return "thermostat #" + str(self._thermostat.get_index())

    @property
    def unique_id(self):
        """Get the unique id."""
        return self._attr_unique_id

    @property
    def temperature_unit(self):
        """Get the temp unit."""
        return TEMP_CELSIUS

    @property
    def current_temperature(self):
        """Get the current temp."""
        return self._thermostat.get_current_temperature()

    @property
    def target_temperature(self):
        """Return the temperature we try to reach."""
        return self._thermostat.get_target_temperature()

    @property
    def target_temperature_step(self):
        """Target temp step."""
        return 0.5

    async def async_set_temperature(self, **kwargs: Any) -> None:
        """Async set temp."""
        if (temperature := kwargs.get(ATTR_TEMPERATURE)) is None:
            return
        await self._thermostat.set_target_temperature(temperature)
        await self.async_update()

    @property
    def hvac_mode(self) -> HVACMode | str | None:
        """HVAC mode getter."""
        return HVACMode.COOL if self._thermostat.is_cooling() else HVACMode.HEAT

    @property
    def hvac_action(self) -> HVACAction | str | None:
        """HVAC action getter."""
        if self._thermostat.is_idle():
            return HVACAction.IDLE
        return HVAC_MODE_TO_HVAC_ACTION[self.hvac_mode]

    async def async_set_preset_mode(self, preset_mode):
        """Async set preset mode."""
        self._attr_preset_mode = preset_mode
        await self._thermostat.set_eco(preset_mode == PRESET_ECO)
        await self.async_update()

    # async def async_set_hvac_mode(self, hvac_mode: HVACMode) -> None:
    #     """Set HVAC mode."""
    #     await self._set({ATTR_HVAC_MODE: hvac_mode})

    async def async_update(self):
        """Retrieve latest state."""
        await self._thermostat.update()
        self.async_write_ha_state()
