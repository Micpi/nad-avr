"""Select platform for NAD AVR enumerated variables."""

from __future__ import annotations

from homeassistant.components.select import SelectEntity
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
    """Set up NAD AVR select entities."""
    runtime = entry.runtime_data
    entities = []
    for variable, meta in COMMANDS.items():
        if "=" not in meta["op"] or not meta["values"]:
            continue
        if set(meta["values"]) in _BOOLEAN_SETS:
            continue
        entities.append(NadVariableSelect(entry, runtime, variable))
    async_add_entities(entities)


class NadVariableSelect(NadEntity, SelectEntity):
    """Select backed by an enumerated NAD variable."""

    def __init__(self, entry: ConfigEntry, runtime, variable: str) -> None:
        super().__init__(entry, runtime)
        self.variable = variable
        self._attr_name = variable_name(variable)
        self._attr_unique_id = f"{entry.entry_id}_{variable_slug(variable)}_select"
        self._attr_options = COMMANDS[variable]["values"]
        self._attr_entity_registry_enabled_default = variable in CORE_VARIABLES

    @property
    def current_option(self) -> str | None:
        """Return the current option."""
        if not self.coordinator.data:
            return None
        value = self.coordinator.data.get(self.variable)
        if value in self.options:
            return value
        return None

    async def async_select_option(self, option: str) -> None:
        """Set the selected option."""
        if option in self.options:
            await self.coordinator.client.set_variable(self.variable, option)

    def select_option(self, option: str) -> None:
        """Sync stub."""
        self.hass.async_create_task(self.async_select_option(option))

