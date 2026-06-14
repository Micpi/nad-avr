"""Button platform for NAD AVR step-only commands."""

from __future__ import annotations

from homeassistant.components.button import ButtonEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .commands import COMMANDS
from .entity import NadEntity, variable_name, variable_slug


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up NAD AVR button entities."""
    runtime = entry.runtime_data
    entities = [NadReconnectButton(entry, runtime)]
    for variable, meta in COMMANDS.items():
        if "=" in meta["op"]:
            continue
        if "+" in meta["op"]:
            entities.append(NadStepButton(entry, runtime, variable, "+"))
        if "-" in meta["op"]:
            entities.append(NadStepButton(entry, runtime, variable, "-"))
    async_add_entities(entities)


class NadReconnectButton(NadEntity, ButtonEntity):
    """Reconnect the NAD transport."""

    _attr_name = "Reconnect"

    def __init__(self, entry: ConfigEntry, runtime) -> None:
        super().__init__(entry, runtime)
        self._attr_unique_id = f"{entry.entry_id}_reconnect"

    async def async_press(self) -> None:
        """Reconnect and refresh."""
        await self.coordinator.client.disconnect()
        await self.coordinator.async_request_refresh()

    def press(self) -> None:
        """Sync stub."""


class NadStepButton(NadEntity, ButtonEntity):
    """Button for a + or - only NAD command."""

    def __init__(self, entry: ConfigEntry, runtime, variable: str, operator: str) -> None:
        super().__init__(entry, runtime)
        self.variable = variable
        self.operator = operator
        direction = "Next" if operator == "+" else "Previous"
        self._attr_name = f"{variable_name(variable)} {direction}"
        self._attr_unique_id = (
            f"{entry.entry_id}_{variable_slug(variable)}_{'plus' if operator == '+' else 'minus'}"
        )
        self._attr_entity_registry_enabled_default = False

    async def async_press(self) -> None:
        """Send the step command."""
        await self.coordinator.client.step_variable(self.variable, self.operator)

    def press(self) -> None:
        """Sync stub."""

