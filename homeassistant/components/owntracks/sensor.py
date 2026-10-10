"""Sensor platform for OwnTracks."""

from typing import Any, override

from homeassistant.components.sensor import (
    DOMAIN as SENSOR_DOMAIN,
    RestoreSensor,
    SensorDeviceClass,
    SensorStateClass,
)
from homeassistant.const import PERCENTAGE
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from . import OwnTracksConfigEntry
from .const import DOMAIN

BATTERY_UNIQUE_ID_SUFFIX = "_battery"


async def async_setup_entry(
    hass: HomeAssistant,
    entry: OwnTracksConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up OwnTracks sensors based on a config entry."""
    # Restore previously added sensors
    ent_reg = er.async_get(hass)
    sensors: dict[str, OwnTracksBatterySensor] = {}
    for entity_entry in er.async_entries_for_config_entry(ent_reg, entry.entry_id):
        if entity_entry.domain == SENSOR_DOMAIN:
            dev_id = entity_entry.unique_id.removesuffix(BATTERY_UNIQUE_ID_SUFFIX)
            sensors[dev_id] = OwnTracksBatterySensor(dev_id)

    @callback
    def _receive_data(dev_id: str, **data: Any) -> None:
        """Update or add a battery sensor."""
        if (sensor := sensors.get(dev_id)) is not None:
            sensor.update_data(data)
            return

        # Beacons and devices which don't report a battery level get no sensor
        if data.get("battery") is None:
            return

        sensor = sensors[dev_id] = OwnTracksBatterySensor(dev_id, data)
        async_add_entities([sensor])

    entry.async_on_unload(entry.runtime_data.async_add_see_listener(_receive_data))

    async_add_entities(sensors.values())


class OwnTracksBatterySensor(RestoreSensor):
    """Represent the battery level of a tracked device."""

    _attr_has_entity_name = True
    _attr_device_class = SensorDeviceClass.BATTERY
    _attr_native_unit_of_measurement = PERCENTAGE
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_should_poll = False

    def __init__(self, dev_id: str, data: dict[str, Any] | None = None) -> None:
        """Set up OwnTracks battery sensor."""
        self._restore = data is None
        self._attr_unique_id = f"{dev_id}{BATTERY_UNIQUE_ID_SUFFIX}"
        self._attr_device_info = DeviceInfo(identifiers={(DOMAIN, dev_id)})
        if data is not None:
            self._attr_native_value = data["battery"]
            if "host_name" in data:
                self._attr_device_info["name"] = data["host_name"]

    @override
    async def async_added_to_hass(self) -> None:
        """Call when entity about to be added to Home Assistant."""
        await super().async_added_to_hass()

        # Don't restore if we got set up with data.
        if not self._restore:
            return

        if (last_sensor_data := await self.async_get_last_sensor_data()) is not None:
            self._attr_native_value = last_sensor_data.native_value

    @callback
    def update_data(self, data: dict[str, Any]) -> None:
        """Update the battery level."""
        # Not all messages carry a battery level
        if (battery := data.get("battery")) is None:
            return

        self._attr_native_value = battery
        if self.hass:
            self.async_write_ha_state()
