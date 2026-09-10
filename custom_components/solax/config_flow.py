"""Config flow for solax integration."""

import logging
from typing import Any, override

import voluptuous as vol
from homeassistant.config_entries import (
    SOURCE_RECONFIGURE,
    ConfigFlow,
    ConfigFlowResult,
)
from homeassistant.const import CONF_IP_ADDRESS, CONF_MODEL, CONF_PASSWORD, CONF_PORT
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers import selector
from solaxng import RealTimeAPI, discover
from solaxng.discovery import DiscoveryError
from solaxng.inverter import Inverter, InverterError

from .const import DOMAIN, friendly_name_for_model, model_name_for_inverter

_LOGGER = logging.getLogger(__name__)

DEFAULT_PORT = 80
DEFAULT_PASSWORD = ""

STEP_USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_IP_ADDRESS): cv.string,
        vol.Optional(CONF_PORT, default=DEFAULT_PORT): cv.port,
        vol.Optional(CONF_PASSWORD, default=DEFAULT_PASSWORD): cv.string,
    }
)


class SolaxConfigFlow(ConfigFlow, domain=DOMAIN):  # pylint: disable=abstract-method
    """Handle a config flow for Solax.

    Three entry points, all funnelled through the same discovery/finalize
    machinery:
    1. ``user`` / ``reconfigure`` - get connection data and do a discovery.
       ``reconfigure`` prefills the form from the entry being reconfigured.
    2. ``select_model`` - shown when step 1's discovery matched multiple
       inverter models; shared by both sources above.

    ``_async_finalize`` branches on ``self.source`` to either create a new
    entry (``user``) or update, reload and abort the existing one
    (``reconfigure``).
    """

    def __init__(self) -> None:
        """Initialize the flow."""
        super().__init__()
        self._connection_data: dict[str, Any] = {}
        self._potential_types: dict[str, Inverter] = {}

    def _select_model_schema(self) -> vol.Schema:
        """Return the schema listing only the discovered inverters."""
        return vol.Schema(
            {
                vol.Required(CONF_MODEL): selector.SelectSelector(
                    selector.SelectSelectorConfig(
                        options=[
                            selector.SelectOptionDict(
                                value=model,
                                label=friendly_name_for_model(model),
                            )
                            for model in sorted(self._potential_types)
                        ],
                        mode=selector.SelectSelectorMode.DROPDOWN,
                    )
                )
            }
        )

    async def _async_finalize(
        self, model: str, inverter: Inverter, *, step_id: str, data_schema: vol.Schema
    ) -> ConfigFlowResult:
        """Fetch the serial number and create the entry, or redisplay on error."""
        errors: dict[str, str] = {}
        try:
            response = await RealTimeAPI(inverter).get_data()
        except ConnectionError, DiscoveryError:
            errors["base"] = "cannot_connect"
        except InverterError as err:
            _LOGGER.debug("Inverter communication error: %s", err)
            errors["base"] = "cannot_connect"
        except Exception:  # pylint: disable=broad-exception-caught
            _LOGGER.exception("Unexpected exception")
            errors["base"] = "unknown"
        else:
            await self.async_set_unique_id(response.serial_number)
            data = {**self._connection_data, CONF_MODEL: model}
            if self.source == SOURCE_RECONFIGURE:
                self._abort_if_unique_id_mismatch(reason="wrong_device")
                return self.async_update_reload_and_abort(
                    self._get_reconfigure_entry(), data_updates=data
                )
            self._abort_if_unique_id_configured()
            return self.async_create_entry(title=response.serial_number, data=data)

        return self.async_show_form(
            step_id=step_id, data_schema=data_schema, errors=errors
        )

    def _connection_schema(self, step_id: str) -> vol.Schema:
        """Return the connection schema, prefilled on the reconfigure path."""
        if step_id == "reconfigure":
            return self.add_suggested_values_to_schema(
                STEP_USER_DATA_SCHEMA, self._get_reconfigure_entry().data
            )
        return STEP_USER_DATA_SCHEMA

    async def _async_step_connection(
        self, step_id: str, user_input: dict[str, Any] | None
    ) -> ConfigFlowResult:
        """Shows the connection form, and do the discovery.

        If discovery resulted in multiple inverters, show the select_model form,
        If only one skip and finalize.
        """
        data_schema = self._connection_schema(step_id)
        if user_input is None:
            return self.async_show_form(step_id=step_id, data_schema=data_schema)

        errors: dict[str, str] = {}
        try:
            potentials = await discover(
                user_input[CONF_IP_ADDRESS],
                user_input[CONF_PORT],
                user_input[CONF_PASSWORD],
            )
        except ConnectionError, DiscoveryError:
            errors["base"] = "cannot_connect"
        except Exception:  # pylint: disable=broad-exception-caught
            _LOGGER.exception("Unexpected exception")
            errors["base"] = "unknown"
        else:
            self._potential_types = {
                model_name_for_inverter(inverter): inverter for inverter in potentials
            }
            self._connection_data = user_input

            if len(self._potential_types) > 1:
                return await self.async_step_select_model()

            model, inverter = next(iter(self._potential_types.items()))
            return await self._async_finalize(
                model, inverter, step_id=step_id, data_schema=data_schema
            )

        return self.async_show_form(
            step_id=step_id, data_schema=data_schema, errors=errors
        )

    @override
    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Shows the connection form, and do the discovery."""
        return await self._async_step_connection("user", user_input)

    async def async_step_reconfigure(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Reconfigure an existing entry by re-running discovery."""
        return await self._async_step_connection("reconfigure", user_input)

    async def async_step_select_model(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle model selection when multiple inverters matched."""
        if user_input is not None:
            model = user_input[CONF_MODEL]
            return await self._async_finalize(
                model,
                self._potential_types[model],
                step_id="select_model",
                data_schema=self._select_model_schema(),
            )

        return self.async_show_form(
            step_id="select_model", data_schema=self._select_model_schema()
        )
