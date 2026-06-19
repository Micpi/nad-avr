"""Sensor platform for NAD AVR variables."""

from __future__ import annotations

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .commands import COMMANDS, QUERYABLE_VARIABLES
from .const import CORE_VARIABLES
from .entity import NadEntity, variable_name, variable_slug


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up NAD AVR sensor entities."""
    runtime = entry.runtime_data
    coordinator = runtime.coordinator
    async_add_entities(
        NadVariableSensor(entry, runtime, variable)
        for variable in QUERYABLE_VARIABLES
        if coordinator.should_create_variable_entity(variable, CORE_VARIABLES)
    )


class NadVariableSensor(NadEntity, SensorEntity):
    """Sensor exposing one queryable NAD variable."""

    def __init__(self, entry: ConfigEntry, runtime, variable: str) -> None:
        super().__init__(entry, runtime)
        self.variable = variable
        self._attr_name = variable_name(variable)
        self._attr_unique_id = f"{entry.entry_id}_{variable_slug(variable)}_sensor"
        self._attr_entity_registry_enabled_default = variable in CORE_VARIABLES

    @property
    def native_value(self) -> str | None:
        """Return the last known variable value."""
        if not self.coordinator.data:
            return None
        return self.coordinator.data.get(self.variable)

    @property
    def extra_state_attributes(self) -> dict[str, str]:
        """Return command metadata."""
        meta = COMMANDS[self.variable]
        return {
            "variable": self.variable,
            "operators": meta["op"],
            "description": meta["desc"],
        }

