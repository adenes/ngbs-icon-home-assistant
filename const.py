"""Constants for the ngbs_icon integration."""

from homeassistant.helpers.entity import DeviceInfo

DOMAIN = "ngbs"

DEVICE_INFO = DeviceInfo(
    identifiers={(DOMAIN,)}, manufacturer="NGBS", model="iCON", name="NGBS iCON"
)
