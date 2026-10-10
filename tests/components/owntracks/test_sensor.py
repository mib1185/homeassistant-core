"""The tests for the OwnTracks sensor platform."""

from typing import Any

from aiohttp.test_utils import TestClient
import pytest

from homeassistant.components.device_tracker.legacy import Device
from homeassistant.components.owntracks import DOMAIN
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er

from tests.common import MockConfigEntry
from tests.typing import ClientSessionGenerator

BATTERY_ENTITY_ID = "sensor.paulus_battery"

LOCATION_MESSAGE = {
    "_type": "location",
    "acc": 60,
    "batt": 92,
    "lon": 45,
    "lat": 90,
    "tid": "test",
    "t": "u",
    "tst": 1,
}

BEACON_TRANSITION_MESSAGE = {
    "_type": "transition",
    "t": "b",
    "lon": 0.0,
    "lat": 0.0,
    "acc": 0.0,
    "batt": 50,
    "event": "enter",
    "tid": "user",
    "desc": "keys",
    "wtst": 1,
    "tst": 2,
}


@pytest.fixture(autouse=True)
def mock_dev_track(mock_device_tracker_conf: list[Device]) -> None:
    """Mock device tracker config loading."""


@pytest.fixture
async def config_entry(hass: HomeAssistant) -> MockConfigEntry:
    """Set up an OwnTracks config entry."""
    entry = MockConfigEntry(
        domain=DOMAIN, data={"webhook_id": "owntracks_test", "secret": "abcd"}
    )
    entry.add_to_hass(hass)

    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    return entry


@pytest.fixture
async def client(
    hass: HomeAssistant,
    hass_client: ClientSessionGenerator,
    config_entry: MockConfigEntry,
) -> TestClient:
    """Return a client to post OwnTracks messages to the webhook."""
    return await hass_client()


async def send_message(
    hass: HomeAssistant, client: TestClient, message: dict[str, Any]
) -> None:
    """Send an OwnTracks message to the webhook."""
    resp = await client.post(
        "/api/webhook/owntracks_test",
        json=message,
        headers={"X-Limit-u": "Paulus", "X-Limit-d": "Pixel"},
    )
    assert resp.status == 200
    await hass.async_block_till_done()


async def test_battery_sensor(
    hass: HomeAssistant,
    entity_registry: er.EntityRegistry,
    client: TestClient,
) -> None:
    """Test the battery sensor is created and updated."""
    await send_message(hass, client, LOCATION_MESSAGE)

    assert hass.states.get(BATTERY_ENTITY_ID).state == "92"
    assert (
        "battery_level" not in hass.states.get("device_tracker.paulus_pixel").attributes
    )
    assert (
        entity_registry.async_get(BATTERY_ENTITY_ID).unique_id == "paulus_pixel_battery"
    )

    await send_message(hass, client, LOCATION_MESSAGE | {"batt": 80})

    assert hass.states.get(BATTERY_ENTITY_ID).state == "80"

    # Messages without a battery level don't reset the sensor
    message = LOCATION_MESSAGE.copy()
    del message["batt"]
    await send_message(hass, client, message)

    assert hass.states.get(BATTERY_ENTITY_ID).state == "80"


async def test_no_battery_sensor_without_battery_level(
    hass: HomeAssistant, client: TestClient
) -> None:
    """Test no battery sensor is created for devices not reporting a battery level."""
    message = LOCATION_MESSAGE.copy()
    del message["batt"]
    await send_message(hass, client, message)

    assert hass.states.get("device_tracker.paulus_pixel") is not None
    assert hass.states.async_entity_ids("sensor") == []


async def test_no_battery_sensor_for_mobile_beacon(
    hass: HomeAssistant, client: TestClient
) -> None:
    """Test no battery sensor is created for a mobile beacon."""
    await send_message(hass, client, LOCATION_MESSAGE)
    await send_message(hass, client, BEACON_TRANSITION_MESSAGE)

    assert hass.states.get("device_tracker.beacon_keys") is not None
    assert hass.states.async_entity_ids("sensor") == [BATTERY_ENTITY_ID]


async def test_restore_battery_level(
    hass: HomeAssistant, config_entry: MockConfigEntry, client: TestClient
) -> None:
    """Test the battery level is restored after a reload."""
    await send_message(hass, client, LOCATION_MESSAGE)

    assert hass.states.get(BATTERY_ENTITY_ID).state == "92"

    assert await hass.config_entries.async_reload(config_entry.entry_id)
    await hass.async_block_till_done()

    assert hass.states.get(BATTERY_ENTITY_ID).state == "92"
