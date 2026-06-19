"""Media player platform for NAD AVR."""

from __future__ import annotations

from typing import Any

from homeassistant.components.media_player import MediaPlayerEntity
from homeassistant.components.media_player.const import MediaPlayerEntityFeature
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import STATE_OFF, STATE_ON
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import SOURCE_MIN, VOLUME_MAX_DB, VOLUME_MIN_DB
from .entity import NadEntity

SUPPORT_NAD = (
    MediaPlayerEntityFeature.TURN_ON
    | MediaPlayerEntityFeature.TURN_OFF
    | MediaPlayerEntityFeature.VOLUME_SET
    | MediaPlayerEntityFeature.VOLUME_STEP
    | MediaPlayerEntityFeature.VOLUME_MUTE
    | MediaPlayerEntityFeature.SELECT_SOURCE
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the NAD AVR media player."""
    async_add_entities([NadAvrMediaPlayer(entry, entry.runtime_data)])


class NadAvrMediaPlayer(NadEntity, MediaPlayerEntity):
    """Main NAD AVR media player entity."""

    _attr_supported_features = SUPPORT_NAD

    def __init__(self, entry: ConfigEntry, runtime) -> None:
        super().__init__(entry, runtime)
        self._attr_name = None
        self._attr_unique_id = f"{entry.entry_id}_media_player"

    @property
    def state(self) -> str | None:
        """Return power state."""
        value = self._value("Main.Power")
        if value == "On":
            return STATE_ON
        if value == "Off":
            return STATE_OFF
        return None

    @property
    def volume_level(self) -> float | None:
        """Return volume mapped from dB range to 0..1."""
        value = self._float_value("Main.Volume")
        if value is None:
            return None
        return max(0.0, min(1.0, (value - VOLUME_MIN_DB) / (VOLUME_MAX_DB - VOLUME_MIN_DB)))

    @property
    def is_volume_muted(self) -> bool | None:
        """Return mute state."""
        value = self._value("Main.Mute")
        if value is None:
            return None
        return value == "On"

    @property
    def source(self) -> str | None:
        """Return selected source."""
        value = self._value("Main.Source")
        return f"Source {value}" if value is not None else None

    @property
    def source_list(self) -> list[str]:
        """Return available source labels."""
        source_max = self.coordinator.model_profile.source_count
        return [f"Source {source}" for source in range(SOURCE_MIN, source_max + 1)]

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return useful AVR attributes."""
        data = self.coordinator.data or {}
        return {
            "model": data.get("Main.Model"),
            "listening_mode": data.get("Main.ListeningMode"),
            "audio_mode": data.get("Main.AudioMode"),
            "video_mode": data.get("Main.VideoMode"),
            "raw_volume_db": data.get("Main.Volume"),
            "query_all_enabled": self.coordinator.query_all,
            "supported_variable_count": len(self.coordinator.supported_variables),
            "profile_model": self.coordinator.model_profile.model,
        }

    async def async_turn_on(self) -> None:
        """Turn the main zone on."""
        await self.coordinator.client.set_variable("Main.Power", "On")

    async def async_turn_off(self) -> None:
        """Turn the main zone off."""
        await self.coordinator.client.set_variable("Main.Power", "Off")

    async def async_set_volume_level(self, volume: float) -> None:
        """Set volume from a 0..1 value."""
        db_value = round(VOLUME_MIN_DB + volume * (VOLUME_MAX_DB - VOLUME_MIN_DB))
        await self.coordinator.client.set_variable("Main.Volume", db_value)

    async def async_volume_up(self) -> None:
        """Increase volume."""
        await self.coordinator.client.step_variable("Main.Volume", "+")

    async def async_volume_down(self) -> None:
        """Decrease volume."""
        await self.coordinator.client.step_variable("Main.Volume", "-")

    async def async_mute_volume(self, mute: bool) -> None:
        """Mute or unmute."""
        await self.coordinator.client.set_variable("Main.Mute", "On" if mute else "Off")

    async def async_select_source(self, source: str) -> None:
        """Select a source."""
        if source.startswith("Source "):
            await self.coordinator.client.set_variable("Main.Source", source.split(" ", 1)[1])

    def turn_on(self) -> None:
        """Sync stub."""

    def turn_off(self) -> None:
        """Sync stub."""

    def set_volume_level(self, volume: float) -> None:
        """Sync stub."""

    def mute_volume(self, mute: bool) -> None:
        """Sync stub."""

    def select_source(self, source: str) -> None:
        """Sync stub."""

    def _value(self, variable: str) -> str | None:
        if not self.coordinator.data:
            return None
        return self.coordinator.data.get(variable)

    def _float_value(self, variable: str) -> float | None:
        value = self._value(variable)
        if value is None:
            return None
        try:
            return float(value)
        except ValueError:
            return None

