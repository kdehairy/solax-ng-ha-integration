"""Fixtures for the solax integration tests."""

from collections.abc import Callable, Iterator, Mapping
from contextlib import contextmanager
from typing import Any
from unittest.mock import MagicMock, patch

import pytest
from homeassistant.const import CONF_IP_ADDRESS, CONF_PASSWORD, CONF_PORT
from pytest_homeassistant_custom_component.common import MockConfigEntry
from solaxng import InverterResponse
from solaxng.inverters import X1MiniV34

from custom_components.solax.const import DOMAIN


@pytest.fixture
def mock_config_entry() -> MockConfigEntry:
    """Return a mock solax config entry."""
    return MockConfigEntry(
        domain=DOMAIN,
        data={
            CONF_IP_ADDRESS: "192.168.1.87",
            CONF_PORT: 80,
            CONF_PASSWORD: "password",
        },
        unique_id="ABCDEFGHIJ",
    )


def _build_inverter(data: Mapping[str, Any]) -> Any:
    """Return an X1 Mini V3.4 instance for the given connection data."""
    return X1MiniV34(
        X1MiniV34.endpoints[0].build(
            data[CONF_IP_ADDRESS],
            data[CONF_PORT],
            data[CONF_PASSWORD],
        )
    )


def _inverter_response() -> InverterResponse:
    """Return a canned X1 Mini V3.4 inverter response."""
    return InverterResponse(
        data=dict.fromkeys(X1MiniV34.sensor_map(), 0),
        dongle_serial_number="ABCDEFGHIJ",
        version="2.034.06",
        type=4,
        inverter_serial_number="XXXXXXX",
    )


@pytest.fixture
def patch_inverter() -> Callable[[Mapping[str, Any]], Any]:
    """Return a helper patching inverter discovery and data retrieval.

    The returned context manager yields the patched ``discover`` mock so tests
    can assert on how discovery was invoked.
    """

    @contextmanager
    def _patch_inverter(data: Mapping[str, Any]) -> Iterator[MagicMock]:
        inverter = _build_inverter(data)
        with (
            patch(
                "custom_components.solax.discover", return_value={inverter}
            ) as mock_discover,
            patch("solaxng.RealTimeAPI.get_data", return_value=_inverter_response()),
        ):
            yield mock_discover

    return _patch_inverter
