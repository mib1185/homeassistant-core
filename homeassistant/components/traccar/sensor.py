"""Support for Traccar Client sensors."""

from typing import override

from homeassistant.components.sensor import (
    RestoreSensor,
    SensorDeviceClass,
    SensorStateClass,
)
from homeassistant.const import PERCENTAGE
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from . import DEFAULT_BATTERY, TRACKER_UPDATE, TraccarConfigEntry
from .const import DOMAIN


async def async_setup_entry(
    hass: HomeAssistant,
    entry: TraccarConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up Traccar Client sensors based on a config entry."""
    devices: set[str] = set()

    @callback
    def _receive_data(device, latitude, longitude, battery, accuracy, attrs):
        """Add a battery sensor for a newly seen device."""
        if device in devices:
            return

        devices.add(device)

        async_add_entities([TraccarBatterySensor(device, battery)])

    entry.async_on_unload(async_dispatcher_connect(hass, TRACKER_UPDATE, _receive_data))

    # Restore previously loaded devices
    dev_reg = dr.async_get(hass)
    dev_ids = {
        identifier[1]
        for device in dr.async_entries_for_config_entry(dev_reg, entry.entry_id)
        for identifier in device.identifiers
    }
    devices.update(dev_ids)

    async_add_entities(TraccarBatterySensor(dev_id, None) for dev_id in dev_ids)


def _battery_level(battery: float | None) -> float | None:
    """Return the battery level, or None if it was not reported."""
    if battery is None or battery == DEFAULT_BATTERY:
        return None
    return battery


class TraccarBatterySensor(RestoreSensor):
    """Represent the battery level of a tracked device."""

    _attr_has_entity_name = True
    _attr_device_class = SensorDeviceClass.BATTERY
    _attr_native_unit_of_measurement = PERCENTAGE
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_should_poll = False

    def __init__(self, device: str, battery: float | None) -> None:
        """Set up Traccar Client battery sensor."""
        self._device = device
        self._restore = battery is None
        self._attr_native_value = _battery_level(battery)
        self._attr_unique_id = f"{device}_battery"
        self._attr_device_info = DeviceInfo(
            name=device,
            identifiers={(DOMAIN, device)},
        )

    @override
    async def async_added_to_hass(self) -> None:
        """Register state update callback."""
        await super().async_added_to_hass()
        self.async_on_remove(
            async_dispatcher_connect(
                self.hass, TRACKER_UPDATE, self._async_receive_data
            )
        )

        # don't restore if we got created with data
        if not self._restore:
            return

        if (last_sensor_data := await self.async_get_last_sensor_data()) is not None:
            self._attr_native_value = last_sensor_data.native_value

    @callback
    def _async_receive_data(
        self, device, latitude, longitude, battery, accuracy, attributes
    ):
        """Update the battery level."""
        if device != self._device:
            return

        self._attr_native_value = _battery_level(battery)
        self.async_write_ha_state()
