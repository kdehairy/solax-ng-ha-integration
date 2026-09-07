"""Tests for the solax sensor platform."""

from collections.abc import Callable, Mapping
from typing import Any
from unittest.mock import patch

from freezegun.api import FrozenDateTimeFactory
from homeassistant.config_entries import ConfigEntryState
from homeassistant.const import STATE_UNAVAILABLE
from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import (
    MockConfigEntry,
    async_fire_time_changed,
)
from solax.inverter import InverterError

from custom_components.solax import SCAN_INTERVAL


async def test_coordinator_update_failure(
    hass: HomeAssistant,
    freezer: FrozenDateTimeFactory,
    mock_config_entry: MockConfigEntry,
    patch_inverter: Callable[[Mapping[str, Any]], Any],
) -> None:
    """Test an InverterError during a refresh marks the entities unavailable."""
    mock_config_entry.add_to_hass(hass)

    with patch_inverter(mock_config_entry.data):
        assert await hass.config_entries.async_setup(mock_config_entry.entry_id)
        await hass.async_block_till_done()

    assert mock_config_entry.state is ConfigEntryState.LOADED

    state = hass.states.get("sensor.solax_abcdefghij_network_voltage")
    assert state is not None
    assert state.state != STATE_UNAVAILABLE

    with patch("solax.RealTimeAPI.get_data", side_effect=InverterError):
        freezer.tick(SCAN_INTERVAL)
        async_fire_time_changed(hass)
        await hass.async_block_till_done()

    state = hass.states.get("sensor.solax_abcdefghij_network_voltage")
    assert state is not None
    assert state.state == STATE_UNAVAILABLE
