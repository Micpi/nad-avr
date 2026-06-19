"""NAD AVR integration for Home Assistant."""

from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST, CONF_NAME, CONF_PORT
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.helpers import config_validation as cv

from .api import NadClient
from .const import (
    CONF_BAUDRATE,
    CONF_CONNECTION_TYPE,
    CONF_MODEL,
    CONF_QUERY_ALL,
    CONF_SERIAL_PORT,
    DEFAULT_BAUDRATE,
    DEFAULT_NAME,
    DEFAULT_PORT,
    DEFAULT_QUERY_ALL,
    DOMAIN,
    MODEL_AUTO,
    PLATFORMS,
)
from .coordinator import NadDataUpdateCoordinator
from .entity import NadRuntimeData

_LOGGER = logging.getLogger(__name__)

SERVICE_SEND_COMMAND = "send_command"
SERVICE_SET_VARIABLE = "set_variable"
SERVICE_QUERY_VARIABLE = "query_variable"
SERVICE_INCREMENT_VARIABLE = "increment_variable"
SERVICE_DECREMENT_VARIABLE = "decrement_variable"
SERVICE_SEND_IR = "send_ir"


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up NAD AVR from a config entry."""
    client = NadClient(
        connection_type=entry.data[CONF_CONNECTION_TYPE],
        host=entry.data.get(CONF_HOST),
        port=entry.data.get(CONF_PORT, DEFAULT_PORT),
        serial_port=entry.data.get(CONF_SERIAL_PORT),
        baudrate=entry.data.get(CONF_BAUDRATE, DEFAULT_BAUDRATE),
    )
    coordinator = NadDataUpdateCoordinator(
        hass,
        client,
        entry.options.get(CONF_QUERY_ALL, entry.data.get(CONF_QUERY_ALL, DEFAULT_QUERY_ALL)),
        entry.data.get(CONF_MODEL, MODEL_AUTO),
    )

    await coordinator.async_config_entry_first_refresh()

    runtime = NadRuntimeData(
        coordinator=coordinator,
        name=entry.data.get(CONF_NAME, DEFAULT_NAME),
        model=entry.data.get(CONF_MODEL, MODEL_AUTO),
    )
    entry.runtime_data = runtime

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    entry.async_on_unload(entry.add_update_listener(_async_reload_entry))
    _async_register_services(hass)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a NAD AVR config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        await entry.runtime_data.coordinator.async_shutdown()
    return unload_ok


async def _async_reload_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Reload a config entry after options changed."""
    await async_unload_entry(hass, entry)
    await async_setup_entry(hass, entry)


def _matching_runtimes(hass: HomeAssistant, entry_id: str | None) -> list[NadRuntimeData]:
    """Return runtimes targeted by a service call."""
    entries = hass.config_entries.async_entries(DOMAIN)
    runtimes: list[NadRuntimeData] = []
    for entry in entries:
        if entry_id and entry.entry_id != entry_id:
            continue
        runtime = getattr(entry, "runtime_data", None)
        if runtime is not None:
            runtimes.append(runtime)
    return runtimes


def _async_register_services(hass: HomeAssistant) -> None:
    """Register integration services once."""
    if hass.services.has_service(DOMAIN, SERVICE_SEND_COMMAND):
        return

    async def send_command(call: ServiceCall) -> None:
        for runtime in _matching_runtimes(hass, call.data.get("entry_id")):
            await runtime.coordinator.client.send_raw(call.data["command"])

    async def set_variable(call: ServiceCall) -> None:
        for runtime in _matching_runtimes(hass, call.data.get("entry_id")):
            await runtime.coordinator.client.set_variable(
                call.data["variable"], call.data["value"]
            )

    async def query_variable(call: ServiceCall) -> None:
        for runtime in _matching_runtimes(hass, call.data.get("entry_id")):
            await runtime.coordinator.client.query(call.data["variable"])

    async def increment_variable(call: ServiceCall) -> None:
        for runtime in _matching_runtimes(hass, call.data.get("entry_id")):
            await runtime.coordinator.client.step_variable(call.data["variable"], "+")

    async def decrement_variable(call: ServiceCall) -> None:
        for runtime in _matching_runtimes(hass, call.data.get("entry_id")):
            await runtime.coordinator.client.step_variable(call.data["variable"], "-")

    async def send_ir(call: ServiceCall) -> None:
        variable = call.data.get("variable", "Main.IR")
        for runtime in _matching_runtimes(hass, call.data.get("entry_id")):
            await runtime.coordinator.client.set_variable(variable, call.data["code"])

    base_schema: dict[Any, Any] = {
        vol.Optional("entry_id"): cv.string,
    }
    hass.services.async_register(
        DOMAIN,
        SERVICE_SEND_COMMAND,
        send_command,
        schema=vol.Schema({**base_schema, vol.Required("command"): cv.string}),
    )
    hass.services.async_register(
        DOMAIN,
        SERVICE_SET_VARIABLE,
        set_variable,
        schema=vol.Schema(
            {**base_schema, vol.Required("variable"): cv.string, vol.Required("value"): cv.string}
        ),
    )
    hass.services.async_register(
        DOMAIN,
        SERVICE_QUERY_VARIABLE,
        query_variable,
        schema=vol.Schema({**base_schema, vol.Required("variable"): cv.string}),
    )
    hass.services.async_register(
        DOMAIN,
        SERVICE_INCREMENT_VARIABLE,
        increment_variable,
        schema=vol.Schema({**base_schema, vol.Required("variable"): cv.string}),
    )
    hass.services.async_register(
        DOMAIN,
        SERVICE_DECREMENT_VARIABLE,
        decrement_variable,
        schema=vol.Schema({**base_schema, vol.Required("variable"): cv.string}),
    )
    hass.services.async_register(
        DOMAIN,
        SERVICE_SEND_IR,
        send_ir,
        schema=vol.Schema(
            {
                **base_schema,
                vol.Required("code"): cv.string,
                vol.Optional("variable", default="Main.IR"): cv.string,
            }
        ),
    )

