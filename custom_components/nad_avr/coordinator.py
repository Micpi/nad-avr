"""Data coordinator for the NAD AVR integration."""

from __future__ import annotations

import logging
from datetime import timedelta
from typing import Any

from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import NadClient, NadConnectionError
from .commands import QUERYABLE_VARIABLES
from .const import CORE_VARIABLES, DEFAULT_SCAN_INTERVAL, DOMAIN

_LOGGER = logging.getLogger(__name__)


class NadDataUpdateCoordinator(DataUpdateCoordinator[dict[str, str]]):
    """Coordinator that keeps the NAD variable cache in Home Assistant."""

    def __init__(
        self,
        hass: HomeAssistant,
        client: NadClient,
        query_all: bool,
        scan_interval: int = DEFAULT_SCAN_INTERVAL,
    ) -> None:
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=scan_interval),
        )
        self.client = client
        self.query_all = query_all
        self.client.register_callback(self._handle_push_update)

    @property
    def supported_variables(self) -> set[str]:
        """Return variables that have answered at least once."""
        return set((self.data or self.client.state).keys())

    def should_create_variable_entity(self, variable: str, core_variables: set[str]) -> bool:
        """Return whether an entity should be created for a protocol variable."""
        if variable not in core_variables and not self.query_all:
            return False
        return variable in self.supported_variables

    @callback
    def _handle_push_update(self, state: dict[str, str]) -> None:
        """Publish state received by the protocol listener."""
        self.async_set_updated_data(state)

    async def _async_update_data(self) -> dict[str, str]:
        """Refresh data from the AVR."""
        try:
            await self.client.connect()
            if self.query_all:
                return await self.client.query_many(QUERYABLE_VARIABLES)
            await self.client.query_many(_core_query_variables())
            return self.client.state
        except NadConnectionError as exc:
            raise UpdateFailed(str(exc)) from exc

    async def async_shutdown(self) -> None:
        """Release runtime resources."""
        self.client.unregister_callback(self._handle_push_update)
        await self.client.disconnect()


def _core_query_variables() -> list[str]:
    """Return core variables that can be queried."""
    return sorted(variable for variable in CORE_VARIABLES if variable in QUERYABLE_VARIABLES)

