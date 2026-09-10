"""Tests for the solax config flow."""

from collections.abc import Mapping
from typing import Any, cast
from unittest.mock import patch

import pytest
from homeassistant import config_entries
from homeassistant.config_entries import ConfigFlowResult
from homeassistant.const import CONF_IP_ADDRESS, CONF_MODEL, CONF_PASSWORD, CONF_PORT
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType
from pytest_homeassistant_custom_component.common import MockConfigEntry
from solaxng import InverterResponse
from solaxng.discovery import DiscoveryError
from solaxng.inverter import Inverter, InverterError
from solaxng.inverters import X1Boost, X1MiniV34

from custom_components.solax.const import DOMAIN

CONNECTION_INPUT: dict[str, str | int] = {
    CONF_IP_ADDRESS: "192.168.1.87",
    CONF_PORT: 80,
    CONF_PASSWORD: "password",
}

NEW_CONNECTION_INPUT: dict[str, str | int] = {
    CONF_IP_ADDRESS: "192.168.1.99",
    CONF_PORT: 80,
    CONF_PASSWORD: "new-password",
}


def _build_inverter(inverter_cls: type[Inverter]) -> Inverter:
    """Build a real inverter instance to use as a discover() return value."""
    return inverter_cls(
        inverter_cls.endpoints[0].build(
            CONNECTION_INPUT[CONF_IP_ADDRESS],
            CONNECTION_INPUT[CONF_PORT],
            CONNECTION_INPUT[CONF_PASSWORD],
        )
    )


def __mock_get_data(serial: str = "ABCDEFGHIJ") -> InverterResponse:
    return InverterResponse(
        data=None,
        dongle_serial_number=serial,
        version="2.034.06",
        type=4,
        inverter_serial_number="XXXXXXX",
    )


def _reconfigure_mock_entry(
    data: Mapping[str, Any] | None = None,
) -> MockConfigEntry:
    """Return a MockConfigEntry matching the default mocked discovery serial."""
    return MockConfigEntry(
        domain=DOMAIN, data=dict(data or CONNECTION_INPUT), unique_id="ABCDEFGHIJ"
    )


async def _start_flow(
    hass: HomeAssistant, entry: MockConfigEntry | None
) -> ConfigFlowResult:
    """Start a user flow, or a reconfigure flow for an added entry."""
    if entry is None:
        return await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": config_entries.SOURCE_USER}
        )
    entry.add_to_hass(hass)
    return cast(ConfigFlowResult, await entry.start_reconfigure_flow(hass))


@pytest.mark.parametrize(
    ("discovered_inverter_classes", "steps", "expected_model"),
    [
        pytest.param({X1MiniV34}, [CONNECTION_INPUT], "x1_mini_v34", id="single_match"),
        pytest.param(
            {X1MiniV34, X1Boost},
            [CONNECTION_INPUT, {CONF_MODEL: "x1_mini_v34"}],
            "x1_mini_v34",
            id="multiple_matches",
        ),
    ],
)
async def test_form_success(
    hass: HomeAssistant,
    discovered_inverter_classes: set[type[Inverter]],
    steps: list[dict[str, str | int]],
    expected_model: str,
) -> None:
    """Test successful discovery and entry creation, with/without a model choice."""
    flow = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert flow["type"] is FlowResultType.FORM
    assert flow["errors"] is None

    discovered = {_build_inverter(cls) for cls in discovered_inverter_classes}

    with (
        patch(
            "custom_components.solax.config_flow.discover",
            return_value=discovered,
        ) as mock_discover,
        patch("solaxng.RealTimeAPI.get_data", return_value=__mock_get_data()),
        patch(
            "custom_components.solax.async_setup_entry",
            return_value=True,
        ) as mock_setup_entry,
    ):
        result = flow
        for step_input in steps:
            result = await hass.config_entries.flow.async_configure(
                result["flow_id"], step_input
            )
        await hass.async_block_till_done()

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == "ABCDEFGHIJ"
    assert result["data"] == {**CONNECTION_INPUT, CONF_MODEL: expected_model}
    assert len(mock_setup_entry.mock_calls) == 1
    assert mock_discover.call_count == 1
    assert mock_discover.call_args.kwargs == {}


@pytest.mark.parametrize(
    ("side_effect", "expected_error"),
    [
        pytest.param(ConnectionError, "cannot_connect", id="cannot_connect"),
        pytest.param(DiscoveryError, "cannot_connect", id="discovery_error"),
        pytest.param(Exception, "unknown", id="unknown"),
    ],
)
@pytest.mark.parametrize(
    "source",
    [
        pytest.param(config_entries.SOURCE_USER, id="user"),
        pytest.param(config_entries.SOURCE_RECONFIGURE, id="reconfigure"),
    ],
)
async def test_discover_error(
    hass: HomeAssistant,
    source: str,
    side_effect: type[Exception],
    expected_error: str,
) -> None:
    """Test discovery failures redisplay the current step with an error."""
    entry = (
        _reconfigure_mock_entry()
        if source == config_entries.SOURCE_RECONFIGURE
        else None
    )
    flow = await _start_flow(hass, entry)
    assert flow["type"] is FlowResultType.FORM
    assert flow["errors"] is None

    with patch("custom_components.solax.config_flow.discover", side_effect=side_effect):
        result = await hass.config_entries.flow.async_configure(
            flow["flow_id"], CONNECTION_INPUT
        )

    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == source
    assert result["errors"] == {"base": expected_error}
    if entry is not None:
        assert len(hass.config_entries.async_entries(DOMAIN)) == 1
        assert entry.data == dict(CONNECTION_INPUT)


@pytest.mark.parametrize(
    ("side_effect", "expected_error"),
    [
        pytest.param(ConnectionError, "cannot_connect", id="cannot_connect"),
        pytest.param(InverterError, "cannot_connect", id="inverter_error"),
        pytest.param(Exception, "unknown", id="unknown"),
    ],
)
@pytest.mark.parametrize(
    ("discovered_inverter_classes", "steps", "single_match"),
    [
        pytest.param({X1MiniV34}, [CONNECTION_INPUT], True, id="single_match"),
        pytest.param(
            {X1MiniV34, X1Boost},
            [CONNECTION_INPUT, {CONF_MODEL: "x1_mini_v34"}],
            False,
            id="multiple_matches",
        ),
    ],
)
@pytest.mark.parametrize(
    "source",
    [
        pytest.param(config_entries.SOURCE_USER, id="user"),
        pytest.param(config_entries.SOURCE_RECONFIGURE, id="reconfigure"),
    ],
)
async def test_finalize_error(
    hass: HomeAssistant,
    source: str,
    discovered_inverter_classes: set[type[Inverter]],
    steps: list[dict[str, str | int]],
    single_match: bool,
    side_effect: type[Exception],
    expected_error: str,
) -> None:
    """Test serial-number fetch failures redisplay the current step with an error."""
    entry = (
        _reconfigure_mock_entry()
        if source == config_entries.SOURCE_RECONFIGURE
        else None
    )
    flow = await _start_flow(hass, entry)
    discovered = {_build_inverter(cls) for cls in discovered_inverter_classes}

    with (
        patch(
            "custom_components.solax.config_flow.discover",
            return_value=discovered,
        ),
        patch("solaxng.RealTimeAPI.get_data", side_effect=side_effect),
    ):
        result = flow
        for step_input in steps:
            result = await hass.config_entries.flow.async_configure(
                result["flow_id"], step_input
            )

    expected_step_id = source if single_match else "select_model"
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == expected_step_id
    assert result["errors"] == {"base": expected_error}
    if entry is not None:
        assert len(hass.config_entries.async_entries(DOMAIN)) == 1
        assert entry.data == dict(CONNECTION_INPUT)


async def test_form_select_model_step_options(hass: HomeAssistant) -> None:
    """Test the select_model step only lists the discovered inverter models."""
    flow = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    discovered = {_build_inverter(X1MiniV34), _build_inverter(X1Boost)}

    with patch(
        "custom_components.solax.config_flow.discover",
        return_value=discovered,
    ):
        result = await hass.config_entries.flow.async_configure(
            flow["flow_id"], CONNECTION_INPUT
        )

    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "select_model"
    data_schema = result["data_schema"]
    assert data_schema is not None
    assert data_schema.schema[CONF_MODEL].config["options"] == [
        {"value": "x1_boost", "label": "X1 Boost"},
        {"value": "x1_mini_v34", "label": "X1 Mini V34"},
    ]


async def test_reconfigure_form_prefilled(hass: HomeAssistant) -> None:
    """Test the reconfigure form is prefilled from the existing entry data."""
    entry = _reconfigure_mock_entry()
    flow = await _start_flow(hass, entry)

    assert flow["type"] is FlowResultType.FORM
    assert flow["step_id"] == "reconfigure"
    data_schema = flow["data_schema"]
    assert data_schema is not None
    for key in data_schema.schema:
        assert key.description == {"suggested_value": CONNECTION_INPUT[key.schema]}


@pytest.mark.parametrize(
    ("discovered_inverter_classes", "steps", "expected_model"),
    [
        pytest.param(
            {X1MiniV34}, [NEW_CONNECTION_INPUT], "x1_mini_v34", id="single_match"
        ),
        pytest.param(
            {X1MiniV34, X1Boost},
            [NEW_CONNECTION_INPUT, {CONF_MODEL: "x1_mini_v34"}],
            "x1_mini_v34",
            id="multiple_matches",
        ),
    ],
)
async def test_reconfigure_success(
    hass: HomeAssistant,
    discovered_inverter_classes: set[type[Inverter]],
    steps: list[dict[str, str | int]],
    expected_model: str,
) -> None:
    """Test reconfigure re-runs discovery and updates+reloads the entry in place."""
    entry = _reconfigure_mock_entry(data={**CONNECTION_INPUT, CONF_MODEL: "x1_boost"})
    flow = await _start_flow(hass, entry)
    assert flow["type"] is FlowResultType.FORM
    assert flow["step_id"] == "reconfigure"

    discovered = {_build_inverter(cls) for cls in discovered_inverter_classes}

    with (
        patch(
            "custom_components.solax.config_flow.discover",
            return_value=discovered,
        ),
        patch("solaxng.RealTimeAPI.get_data", return_value=__mock_get_data()),
        patch(
            "custom_components.solax.async_setup_entry",
            return_value=True,
        ) as mock_setup_entry,
    ):
        result = flow
        for step_input in steps:
            result = await hass.config_entries.flow.async_configure(
                result["flow_id"], step_input
            )
        await hass.async_block_till_done()

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "reconfigure_successful"
    assert entry.data == {**NEW_CONNECTION_INPUT, CONF_MODEL: expected_model}
    assert len(hass.config_entries.async_entries(DOMAIN)) == 1
    assert len(mock_setup_entry.mock_calls) == 1


async def test_reconfigure_wrong_device(hass: HomeAssistant) -> None:
    """Test reconfigure aborts wrong_device when discovery finds a different unit."""
    entry = _reconfigure_mock_entry()
    flow = await _start_flow(hass, entry)

    discovered = {_build_inverter(X1MiniV34)}
    mismatched_response = __mock_get_data(serial="ZZZZZZZZZZ")

    with (
        patch(
            "custom_components.solax.config_flow.discover",
            return_value=discovered,
        ),
        patch("solaxng.RealTimeAPI.get_data", return_value=mismatched_response),
        patch(
            "custom_components.solax.async_setup_entry", return_value=True
        ) as mock_setup_entry,
    ):
        result = await hass.config_entries.flow.async_configure(
            flow["flow_id"], CONNECTION_INPUT
        )

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "wrong_device"
    assert entry.data == dict(CONNECTION_INPUT)
    assert mock_setup_entry.mock_calls == []
