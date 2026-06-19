"""Data coordinator for the NAD AVR integration."""

from __future__ import annotations

import logging
from datetime import timedelta
from typing import Any

from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import NadClient, NadConnectionError
from .commands import QUERYABLE_VARIABLES
from .const import CORE_VARIABLES, DEFAULT_SCAN_INTERVAL, DOMAIN, MODEL_AUTO
from .model_profiles import model_query_variables, possible_model_variables, profile_for_model

_LOGGER = logging.getLogger(__name__)

CORE_COMMAND_DELAY = 0.04
FULL_COMMAND_DELAY = 0.04
SCAN_SETTLE_TIME = 1.0


class NadDataUpdateCoordinator(DataUpdateCoordinator[dict[str, str]]):
    """Coordinator that keeps the NAD variable cache in Home Assistant."""

    def __init__(
        self,
        hass: HomeAssistant,
        client: NadClient,
        query_all: bool,
        configured_model: str = MODEL_AUTO,
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
        self.configured_model = configured_model
        self._probe_complete = False
        self._supported_variables: set[str] = set()
        self._last_probe_variables: list[str] = []
        self.client.register_callback(self._handle_push_update)

    @property
    def supported_variables(self) -> set[str]:
        """Return variables that have answered at least once."""
        return self._supported_variables | set((self.data or self.client.state).keys())

    @property
    def detected_model(self) -> str:
        """Return the detected model, falling back to the configured model."""
        return (self.data or self.client.state).get("Main.Model", self.configured_model)

    @property
    def model_profile(self):
        """Return the active static model profile."""
        return profile_for_model(self.detected_model)

    @property
    def possible_variables(self) -> list[str]:
        """Return variables allowed by the current static model profile."""
        return possible_model_variables(self.detected_model)

    @property
    def probed_variables(self) -> list[str]:
        """Return variables queried during the last capability probe."""
        return self._last_probe_variables

    def should_create_variable_entity(self, variable: str, core_variables: set[str]) -> bool:
        """Return whether an entity should be created for a protocol variable."""
        if not self.query_all and not self.model_profile.allows_variable(variable):
            return False
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
            if not self._probe_complete:
                variables = model_query_variables(self.configured_model, self.query_all)
                self._last_probe_variables = variables
                await self.client.scan_many(
                    variables,
                    command_delay=FULL_COMMAND_DELAY if self.query_all else CORE_COMMAND_DELAY,
                    settle_time=SCAN_SETTLE_TIME,
                )
                self._supported_variables = set(self.client.state)
                self._probe_complete = True
                _LOGGER.info(
                    "NAD capability probe found %d supported variables",
                    len(self._supported_variables),
                )
                return self.client.state

            variables = sorted(
                variable
                for variable in self.supported_variables
                if variable in QUERYABLE_VARIABLES
                and (self.query_all or self.model_profile.allows_variable(variable))
            )
            await self.client.scan_many(variables, settle_time=SCAN_SETTLE_TIME)
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

