"""The tests for the GPSLogger sensor platform."""

import pytest

from homeassistant.components.device_tracker.legacy import Device
from homeassistant.components.gpslogger import DOMAIN
from homeassistant.const import CONF_WEBHOOK_ID, PERCENTAGE, STATE_UNKNOWN
from homeassistant.core import HomeAssistant, State
from homeassistant.helpers import device_registry as dr

from tests.common import MockConfigEntry, mock_restore_cache_with_extra_data

DEVICE_ID = "device_1"
ENTITY_ID = f"sensor.{DEVICE_ID}_battery"


@pytest.fixture(autouse=True)
def mock_dev_track(mock_device_tracker_conf: list[Device]) -> None:
    """Mock device tracker config loading."""


@pytest.fixture
def config_entry(
    hass: HomeAssistant, device_registry: dr.DeviceRegistry
) -> MockConfigEntry:
    """Add a config entry with a previously seen device."""
    entry = MockConfigEntry(domain=DOMAIN, data={CONF_WEBHOOK_ID: "webhook_id"})
    entry.add_to_hass(hass)
    device_registry.async_get_or_create(
        config_entry_id=entry.entry_id,
        identifiers={(DOMAIN, DEVICE_ID)},
        name=DEVICE_ID,
    )
    return entry


async def test_restore_battery_level(
    hass: HomeAssistant, config_entry: MockConfigEntry
) -> None:
    """Test that the battery level is restored for a known device."""
    mock_restore_cache_with_extra_data(
        hass,
        [
            (
                State(ENTITY_ID, "40"),
                {"native_value": 40, "native_unit_of_measurement": PERCENTAGE},
            )
        ],
    )

    assert await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()

    assert hass.states.get(ENTITY_ID).state == "40"


async def test_no_battery_level_to_restore(
    hass: HomeAssistant, config_entry: MockConfigEntry
) -> None:
    """Test the battery level is unknown if there is nothing to restore."""
    assert await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()

    assert hass.states.get(ENTITY_ID).state == STATE_UNKNOWN
