"""The ngbs_icon integration."""

from datetime import timedelta
import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST, CONF_PORT, Platform
from homeassistant.core import HomeAssistant
import homeassistant.helpers.config_validation as cv

from .lib.ngbs import NGBSController

_LOGGER = logging.getLogger(__name__)

PARALLEL_UPDATES = 0
MIN_TIME_BETWEEN_UPDATES = timedelta(seconds=60)

PLATFORMS = [Platform.CLIMATE, Platform.SENSOR]
DOMAIN = "ngbs"

CONFIG_SCHEMA = cv.removed(DOMAIN, raise_if_present=False)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Async setup."""
    conf = entry.data

    ngbs_controller = NGBSController(hass, conf[CONF_HOST], conf[CONF_PORT])
    if not ngbs_controller:
        return False

    await ngbs_controller.initialize()

    hass.data.setdefault(DOMAIN, {}).update({entry.entry_id: ngbs_controller})
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)
        if not hass.data[DOMAIN]:
            hass.data.pop(DOMAIN)
    return unload_ok


# from __future__ import annotations

# from homeassistant.config_entries import ConfigEntry
# from homeassistant.const import Platform
# from homeassistant.core import HomeAssistant

# PLATFORMS = [Platform.CLIMATE]


# async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
#     await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
#     return True


# async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
#     """Unload a config entry."""
#     return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
