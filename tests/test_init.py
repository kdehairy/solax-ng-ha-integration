"""Tests for the solax integration setup."""

from collections.abc import Callable, Mapping
from typing import Any
from unittest.mock import patch

import pytest
from homeassistant.config_entries import ConfigEntryState
from homeassistant.const import CONF_IP_ADDRESS, CONF_MODEL, CONF_PASSWORD, CONF_PORT
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr
from pytest_homeassistant_custom_component.common import MockConfigEntry
from solax.inverters import X1MiniV34

from custom_components.solax.const import DOMAIN


@pytest.mark.parametrize(
    ("entry_data", "expected_inverters"),
    [
        pytest.param(
            {CONF_IP_ADDRESS: "192.168.1.87", CONF_PORT: 80, CONF_PASSWORD: "password"},
            None,
            id="auto_detect",
        ),
        pytest.param(
            {
                CONF_IP_ADDRESS: "192.168.1.87",
                CONF_PORT: 80,
                CONF_PASSWORD: "password",
                CONF_MODEL: "x1_mini_v34",
            },
            [X1MiniV34],
            id="model_selected",
        ),
    ],
)
async def test_setup_entry_success(
    hass: HomeAssistant,
    entry_data: dict[str, str | int],
    expected_inverters: list[type] | None,
    patch_inverter: Callable[[Mapping[str, Any]], Any],
) -> None:
    """Test the entry loads and discover() is called with the right inverters."""
    entry = MockConfigEntry(domain=DOMAIN, data=entry_data, unique_id="ABCDEFGHIJ")
    entry.add_to_hass(hass)

    with patch_inverter(entry_data) as mock_discover:
        assert await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()

    assert entry.state is ConfigEntryState.LOADED
    assert mock_discover.call_args.kwargs.get("inverters") == expected_inverters


async def test_device_info_model(
    hass: HomeAssistant,
    device_registry: dr.DeviceRegistry,
    mock_config_entry: MockConfigEntry,
    patch_inverter: Callable[[Mapping[str, Any]], Any],
) -> None:
    """Test the device registry entry has the discovered inverter model set."""
    mock_config_entry.add_to_hass(hass)

    with patch_inverter(mock_config_entry.data):
        assert await hass.config_entries.async_setup(mock_config_entry.entry_id)
        await hass.async_block_till_done()

    device = device_registry.async_get_device_by_identifier(
        (DOMAIN, "ABCDEFGHIJ"), mock_config_entry.entry_id
    )
    assert device is not None
    assert device.model == "x1_mini_v34"


async def test_setup_entry_not_ready(
    hass: HomeAssistant, mock_config_entry: MockConfigEntry
) -> None:
    """Test ConfigEntryNotReady is raised when discovery fails."""
    mock_config_entry.add_to_hass(hass)

    with patch("custom_components.solax.discover", side_effect=ConnectionError):
        assert not await hass.config_entries.async_setup(mock_config_entry.entry_id)
        await hass.async_block_till_done()

    assert mock_config_entry.state is ConfigEntryState.SETUP_RETRY
