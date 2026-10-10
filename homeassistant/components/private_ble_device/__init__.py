"""Private BLE Device integration."""

from homeassistant.const import Platform
from homeassistant.core import HomeAssistant

from .coordinator import PrivateBLEDeviceConfigEntry, async_get_coordinator

PLATFORMS = [Platform.DEVICE_TRACKER, Platform.SENSOR]


async def async_setup_entry(
    hass: HomeAssistant, entry: PrivateBLEDeviceConfigEntry
) -> bool:
    """Set up tracking of a private bluetooth device from a config entry."""
    entry.runtime_data = async_get_coordinator(hass)
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(
    hass: HomeAssistant, entry: PrivateBLEDeviceConfigEntry
) -> bool:
    """Unload entities for a config entry."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
