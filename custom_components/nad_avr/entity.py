"""Shared entities for the NAD AVR integration."""

from __future__ import annotations

import re
from dataclasses import dataclass

from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, MANUFACTURER
from .coordinator import NadDataUpdateCoordinator


@dataclass(frozen=True)
class NadRuntimeData:
    """Runtime data stored on a config entry."""

    coordinator: NadDataUpdateCoordinator
    name: str
    model: str


def variable_slug(variable: str) -> str:
    """Convert a NAD variable name into a stable slug suffix."""
    return re.sub(r"[^a-z0-9]+", "_", variable.lower()).strip("_")


def variable_name(variable: str) -> str:
    """Convert a NAD variable name into a readable entity name."""
    return variable.replace(".", " ")


class NadEntity(CoordinatorEntity[NadDataUpdateCoordinator]):
    """Base class for NAD entities."""

    _attr_has_entity_name = True

    def __init__(self, entry: ConfigEntry, runtime: NadRuntimeData) -> None:
        super().__init__(runtime.coordinator)
        self.entry = entry
        self.runtime = runtime

    @property
    def device_info(self) -> DeviceInfo:
        """Return the NAD device info."""
        return DeviceInfo(
            identifiers={(DOMAIN, self.entry.unique_id or self.entry.entry_id)},
            name=self.runtime.name,
            manufacturer=MANUFACTURER,
            model=self.coordinator.data.get("Main.Model", self.runtime.model)
            if self.coordinator.data
            else self.runtime.model,
        )

    @property
    def available(self) -> bool:
        """Return whether the device is available."""
        return self.coordinator.client.is_connected

