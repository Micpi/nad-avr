"""Config flow for the NAD AVR integration."""

from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol
from homeassistant.config_entries import ConfigEntry, ConfigFlow, ConfigFlowResult, OptionsFlow
from homeassistant.const import CONF_HOST, CONF_NAME, CONF_PORT
from homeassistant.core import callback
from homeassistant.helpers import selector

from .api import NadClient, NadConnectionError
from .const import (
    CONF_BAUDRATE,
    CONF_CONNECTION_TYPE,
    CONF_MODEL,
    CONF_QUERY_ALL,
    CONF_SERIAL_PORT,
    CONNECTION_RS232,
    CONNECTION_TELNET,
    CONNECTION_TYPES,
    DEFAULT_BAUDRATE,
    DEFAULT_NAME,
    DEFAULT_PORT,
    DEFAULT_QUERY_ALL,
    DOMAIN,
    MODEL_AUTO,
    MODELS,
)

_LOGGER = logging.getLogger(__name__)


class NadAvrConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for NAD AVR."""

    VERSION = 1

    def __init__(self) -> None:
        self._connection_type = CONNECTION_TELNET

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Choose the transport."""
        if user_input is not None:
            self._connection_type = user_input[CONF_CONNECTION_TYPE]
            if self._connection_type == CONNECTION_RS232:
                return await self.async_step_rs232()
            return await self.async_step_telnet()

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        CONF_CONNECTION_TYPE, default=CONNECTION_TELNET
                    ): selector.SelectSelector(
                        selector.SelectSelectorConfig(
                            options=CONNECTION_TYPES,
                            mode=selector.SelectSelectorMode.DROPDOWN,
                        )
                    )
                }
            ),
        )

    async def async_step_telnet(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Configure a Telnet/raw TCP connection."""
        errors: dict[str, str] = {}
        if user_input is not None:
            data = {
                **user_input,
                CONF_CONNECTION_TYPE: CONNECTION_TELNET,
            }
            return await self._validate_and_create(data, errors)

        return self.async_show_form(
            step_id="telnet",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_HOST): str,
                    vol.Required(CONF_PORT, default=DEFAULT_PORT): int,
                    vol.Required(CONF_NAME, default=DEFAULT_NAME): str,
                    vol.Optional(CONF_MODEL, default=MODEL_AUTO): selector.SelectSelector(
                        selector.SelectSelectorConfig(options=MODELS)
                    ),
                    vol.Optional(CONF_QUERY_ALL, default=DEFAULT_QUERY_ALL): bool,
                }
            ),
            errors=errors,
        )

    async def async_step_rs232(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Configure an RS-232 serial connection."""
        errors: dict[str, str] = {}
        if user_input is not None:
            data = {
                **user_input,
                CONF_CONNECTION_TYPE: CONNECTION_RS232,
            }
            return await self._validate_and_create(data, errors)

        return self.async_show_form(
            step_id="rs232",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_SERIAL_PORT): str,
                    vol.Required(CONF_BAUDRATE, default=DEFAULT_BAUDRATE): int,
                    vol.Required(CONF_NAME, default=DEFAULT_NAME): str,
                    vol.Optional(CONF_MODEL, default=MODEL_AUTO): selector.SelectSelector(
                        selector.SelectSelectorConfig(options=MODELS)
                    ),
                    vol.Optional(CONF_QUERY_ALL, default=DEFAULT_QUERY_ALL): bool,
                }
            ),
            errors=errors,
        )

    async def _validate_and_create(
        self, data: dict[str, Any], errors: dict[str, str]
    ) -> ConfigFlowResult:
        """Validate connection details and create the entry."""
        client = NadClient(
            connection_type=data[CONF_CONNECTION_TYPE],
            host=data.get(CONF_HOST),
            port=data.get(CONF_PORT, DEFAULT_PORT),
            serial_port=data.get(CONF_SERIAL_PORT),
            baudrate=data.get(CONF_BAUDRATE, DEFAULT_BAUDRATE),
        )
        detected_model = data.get(CONF_MODEL, MODEL_AUTO)
        try:
            await client.connect()
            model = await client.query("Main.Model")
            if model:
                detected_model = model
        except NadConnectionError:
            _LOGGER.warning("NAD AVR is unreachable during setup, creating entry anyway")
        except Exception as exc:  # pylint: disable=broad-except
            _LOGGER.debug("NAD setup probe failed: %s", exc)
        finally:
            await client.disconnect()

        unique_target = data.get(CONF_HOST) or data.get(CONF_SERIAL_PORT)
        await self.async_set_unique_id(f"nad_avr_{unique_target}")
        self._abort_if_unique_id_configured()

        data[CONF_MODEL] = detected_model
        return self.async_create_entry(
            title=data.get(CONF_NAME, DEFAULT_NAME),
            data=data,
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> OptionsFlow:
        """Return the options flow."""
        return NadAvrOptionsFlow(config_entry)


class NadAvrOptionsFlow(OptionsFlow):
    """Handle NAD AVR options."""

    def __init__(self, config_entry: ConfigEntry) -> None:
        self.config_entry = config_entry

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Manage options."""
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {
                    vol.Optional(
                        CONF_QUERY_ALL,
                        default=self.config_entry.options.get(
                            CONF_QUERY_ALL,
                            self.config_entry.data.get(CONF_QUERY_ALL, DEFAULT_QUERY_ALL),
                        ),
                    ): bool,
                }
            ),
        )

