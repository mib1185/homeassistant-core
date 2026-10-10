"""The DLNA Digital Media Server integration.

A single config entry is used, with SSDP discovery for media servers. Each
server is wrapped in a DmsEntity, and the server's USN is used as the unique_id.
"""

from homeassistant.core import HomeAssistant

from .const import CONF_SOURCE_ID, LOGGER
from .dms import DlnaDmsConfigEntry, DmsDeviceSource
from .util import generate_source_id


async def async_setup_entry(hass: HomeAssistant, entry: DlnaDmsConfigEntry) -> bool:
    """Set up DLNA DMS device from a config entry."""
    LOGGER.debug("Setting up config entry: %s", entry.unique_id)

    # Soft-migrate entry if it's missing data keys
    if CONF_SOURCE_ID not in entry.data:
        LOGGER.debug("Adding CONF_SOURCE_ID to entry %s", entry.data)
        data = dict(entry.data)
        data[CONF_SOURCE_ID] = generate_source_id(hass, entry.title)
        hass.config_entries.async_update_entry(entry, data=data)

    device = DmsDeviceSource(hass, entry)
    await device.async_added_to_hass()
    entry.runtime_data = device
    return True


async def async_unload_entry(hass: HomeAssistant, entry: DlnaDmsConfigEntry) -> bool:
    """Unload a config entry."""
    LOGGER.debug("Unloading config entry: %s", entry.unique_id)

    await entry.runtime_data.async_will_remove_from_hass()
    return True
