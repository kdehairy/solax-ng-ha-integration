"""The solax component."""

import logging
from dataclasses import dataclass
from datetime import timedelta
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    CONF_IP_ADDRESS,
    CONF_MODEL,
    CONF_PASSWORD,
    CONF_PORT,
    Platform,
)
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryError, ConfigEntryNotReady
from homeassistant.helpers.update_coordinator import UpdateFailed
from solaxng import InverterResponse, RealTimeAPI, discover
from solaxng.inverter import InverterError

from .const import DOMAIN, INVERTER_MODELS, model_name_for_inverter
from .coordinator import SolaxDataUpdateCoordinator

PLATFORMS = [Platform.SENSOR]

SCAN_INTERVAL = timedelta(seconds=30)


@dataclass(slots=True)
class SolaxData:
    """Class for storing solax data."""

    api: RealTimeAPI
    coordinator: SolaxDataUpdateCoordinator


type SolaxConfigEntry = ConfigEntry[SolaxData]

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass: HomeAssistant, entry: SolaxConfigEntry) -> bool:
    """Set up the sensors from a ConfigEntry."""

    # Guard against an unknown stored model key
    model = entry.data.get(CONF_MODEL)
    if model and model not in INVERTER_MODELS:
        raise ConfigEntryError(
            translation_domain=DOMAIN,
            translation_key="unknown_model",
            translation_placeholders={"model": model},
        )

    kwargs: dict[str, Any] = {}
    if model:
        kwargs["inverters"] = [INVERTER_MODELS[model].load()]

    try:
        inverters = await discover(
            entry.data[CONF_IP_ADDRESS],
            entry.data[CONF_PORT],
            entry.data[CONF_PASSWORD],
            **kwargs,
        )
    except Exception as err:
        raise ConfigEntryNotReady from err

    # This branch is only reachable when no CONF_MODEL is stored.
    if len(inverters) > 1:
        matches = sorted(
            f"{inverter.friendly_name()} ({model_name_for_inverter(inverter)})"
            for inverter in inverters
        )
        raise ConfigEntryError(
            translation_domain=DOMAIN,
            translation_key="multiple_matches",
            translation_placeholders={"matches": ", ".join(matches)},
        )

    api = RealTimeAPI(next(iter(inverters)))

    async def _async_update() -> InverterResponse:
        try:
            return await api.get_data()
        except InverterError as err:
            raise UpdateFailed from err

    coordinator = SolaxDataUpdateCoordinator(
        hass,
        logger=_LOGGER,
        config_entry=entry,
        name=f"solax {entry.title}",
        update_interval=SCAN_INTERVAL,
        update_method=_async_update,
    )
    await coordinator.async_config_entry_first_refresh()

    entry.runtime_data = SolaxData(api=api, coordinator=coordinator)
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: SolaxConfigEntry) -> bool:
    """Unload a config entry."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
