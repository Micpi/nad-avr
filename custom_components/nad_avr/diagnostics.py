"""Diagnostics support for the NAD AVR integration."""

from __future__ import annotations

from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST, CONF_PORT
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import async_entries_for_config_entry, async_get
from homeassistant.helpers.diagnostics import async_redact_data

from .const import CONF_BAUDRATE, CONF_SERIAL_PORT

TO_REDACT = {CONF_HOST, CONF_PORT, CONF_SERIAL_PORT, CONF_BAUDRATE}


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant,
    entry: ConfigEntry,
) -> dict[str, Any]:
    """Return diagnostics for a NAD AVR config entry."""
    runtime = entry.runtime_data
    coordinator = runtime.coordinator
    profile = coordinator.model_profile
    supported = sorted(coordinator.supported_variables)
    possible = coordinator.possible_variables
    probed = coordinator.probed_variables
    missing_from_probe = sorted(variable for variable in probed if variable not in supported)

    return {
        "entry": {
            "data": async_redact_data(dict(entry.data), TO_REDACT),
            "options": async_redact_data(dict(entry.options), TO_REDACT),
        },
        "device_registry": [
            {
                "name": device.name,
                "model": device.model,
                "manufacturer": device.manufacturer,
            }
            for device in async_entries_for_config_entry(
                async_get(hass), entry.entry_id
            )
        ],
        "profile": {
            "configured_model": coordinator.configured_model,
            "detected_model": coordinator.detected_model,
            "active_profile": profile.model,
            "zones": list(profile.zones),
            "source_count": profile.source_count,
            "notes": list(profile.notes),
            "possible_variable_count": len(possible),
            "possible_variables": possible,
        },
        "probe": {
            "query_all_enabled": coordinator.query_all,
            "probed_variable_count": len(probed),
            "probed_variables": probed,
            "supported_variable_count": len(supported),
            "supported_variables": supported,
            "missing_from_probe_count": len(missing_from_probe),
            "missing_from_probe": missing_from_probe,
        },
        "state": dict(coordinator.data or {}),
    }
