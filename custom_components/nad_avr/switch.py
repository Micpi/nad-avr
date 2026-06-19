"""Switch platform for NAD AVR boolean variables."""

from __future__ import annotations

from typing import Any

from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .commands import COMMANDS
from .const import CORE_VARIABLES
from .entity import NadEntity, variable_name, variable_slug

_BOOLEAN_SETS = ({"On", "Off"}, {"Yes", "No"})


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up NAD AVR switch entities."""
    runtime = entry.runtime_data
    coordinator = runtime.coordinator
    entities = []
    for variable, meta in COMMANDS.items():
        if "=" not in meta["op"] or set(meta["values"]) not in _BOOLEAN_SETS:
            continue
        if not coordinator.should_create_variable_entity(variable, CORE_VARIABLES):
            continue
        entities.append(NadVariableSwitch(entry, runtime, variable))
    async_add_entities(entities)


class NadVariableSwitch(NadEntity, SwitchEntity):
    """Switch backed by an On/Off or Yes/No NAD variable."""

    def __init__(self, entry: ConfigEntry, runtime, variable: str) -> None:
        super().__init__(entry, runtime)
        self.variable = variable
        values = COMMANDS[variable]["values"]
        self._on_value = "Yes" if "Yes" in values else "On"
        self._off_value = "No" if "No" in values else "Off"
        self._attr_name = variable_name(variable)
        self._attr_unique_id = f"{entry.entry_id}_{variable_slug(variable)}_switch"
        self._attr_entity_registry_enabled_default = variable in CORE_VARIABLES

    @property
    def is_on(self) -> bool | None:
        """Return true if the current value is the on value."""
        if not self.coordinator.data:
            return None
        value = self.coordinator.data.get(self.variable)
        if value is None:
            return None
        return value == self._on_value

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn the variable on."""
        await self.coordinator.client.set_variable(self.variable, self._on_value)

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn the variable off."""
        await self.coordinator.client.set_variable(self.variable, self._off_value)

    def turn_on(self, **kwargs: Any) -> None:
        """Sync stub."""

    def turn_off(self, **kwargs: Any) -> None:
        """Sync stub."""

