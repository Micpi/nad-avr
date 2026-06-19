"""Number platform for NAD AVR ranged variables."""

from __future__ import annotations

from homeassistant.components.number import NumberEntity, NumberMode
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .commands import COMMANDS
from .const import CORE_VARIABLES
from .entity import NadEntity, variable_name, variable_slug


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up NAD AVR number entities."""
    runtime = entry.runtime_data
    coordinator = runtime.coordinator
    async_add_entities(
        NadVariableNumber(entry, runtime, variable)
        for variable, meta in COMMANDS.items()
        if "=" in meta["op"] and meta["range"] is not None
        and coordinator.should_create_variable_entity(variable, CORE_VARIABLES)
    )


class NadVariableNumber(NadEntity, NumberEntity):
    """Number backed by a ranged NAD variable."""

    _attr_mode = NumberMode.BOX

    def __init__(self, entry: ConfigEntry, runtime, variable: str) -> None:
        super().__init__(entry, runtime)
        meta = COMMANDS[variable]
        minimum, maximum = meta["range"]
        self.variable = variable
        self._attr_name = variable_name(variable)
        self._attr_unique_id = f"{entry.entry_id}_{variable_slug(variable)}_number"
        self._attr_native_min_value = float(minimum)
        self._attr_native_max_value = float(maximum)
        self._attr_native_step = float(meta["step"] or 1)
        self._attr_entity_registry_enabled_default = variable in CORE_VARIABLES

    @property
    def native_value(self) -> float | None:
        """Return the current numeric value."""
        if not self.coordinator.data:
            return None
        value = self.coordinator.data.get(self.variable)
        if value is None:
            return None
        try:
            return float(value)
        except ValueError:
            return None

    async def async_set_native_value(self, value: float) -> None:
        """Set the numeric variable."""
        payload: int | float = int(value) if value.is_integer() else value
        await self.coordinator.client.set_variable(self.variable, payload)

    def set_native_value(self, value: float) -> None:
        """Sync stub."""

