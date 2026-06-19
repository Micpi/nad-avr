"""Model capability profiles for NAD AVR receivers."""

from __future__ import annotations

from dataclasses import dataclass, field

from .commands import COMMANDS, QUERYABLE_VARIABLES
from .const import CORE_VARIABLES, MODEL_AUTO


@dataclass(frozen=True)
class ModelProfile:
    """Static capability hints for a NAD AVR model."""

    model: str
    source_count: int = 10
    zones: tuple[str, ...] = ("Main", "Zone2", "Zone3", "Zone4")
    aliases: tuple[str, ...] = ()
    notes: tuple[str, ...] = ()
    extra_core_variables: frozenset[str] = field(default_factory=frozenset)
    disabled_prefixes: tuple[str, ...] = ()
    disabled_variables: frozenset[str] = field(default_factory=frozenset)

    @property
    def core_variables(self) -> set[str]:
        """Return variables worth probing during the normal profile scan."""
        variables = set(CORE_VARIABLES) | set(self.extra_core_variables)
        return {variable for variable in variables if self.allows_variable(variable)}

    def allows_variable(self, variable: str) -> bool:
        """Return whether the static profile allows a protocol variable."""
        if variable in self.disabled_variables:
            return False
        if variable.startswith("Zone"):
            zone = variable.split(".", 1)[0]
            if zone not in self.zones:
                return False
        return not any(variable.startswith(prefix) for prefix in self.disabled_prefixes)


_TXX7_NOTES = (
    "Profile based on the bundled NAD T187/T777/T787 command documents.",
    "Runtime probing is still authoritative for module-dependent features.",
)

_T758_NOTES = (
    "Profile based on the T758/T758 V3/V3i manuals plus runtime probing.",
    "NAD does not expose a complete capability-list command, so answered variables win.",
)

LISTENING_MODE_FAMILY_VARIABLES = frozenset(
    {
        "Main.ListeningMode.Analog",
        "Main.ListeningMode.Digital",
        "Main.ListeningMode.DolbyDigital",
        "Main.ListeningMode.DolbyDigital2ch",
        "Main.ListeningMode.DTS",
    }
)

MODEL_PROFILES: dict[str, ModelProfile] = {
    MODEL_AUTO: ModelProfile(
        model=MODEL_AUTO,
        notes=("Auto profile: uses a conservative core probe, then the detected model.",),
        extra_core_variables=LISTENING_MODE_FAMILY_VARIABLES,
    ),
    "T187": ModelProfile(
        model="T187",
        notes=_TXX7_NOTES,
        extra_core_variables=LISTENING_MODE_FAMILY_VARIABLES,
    ),
    "T758": ModelProfile(
        model="T758",
        aliases=("T758V3", "T758V3I", "T758 V3", "T758 V3I"),
        notes=_T758_NOTES,
        zones=("Main", "Zone2"),
        extra_core_variables=LISTENING_MODE_FAMILY_VARIABLES,
    ),
    "T777": ModelProfile(
        model="T777",
        notes=_TXX7_NOTES,
        extra_core_variables=LISTENING_MODE_FAMILY_VARIABLES,
    ),
    "T787": ModelProfile(
        model="T787",
        notes=_TXX7_NOTES,
        extra_core_variables=LISTENING_MODE_FAMILY_VARIABLES,
    ),
}


def normalize_model(model: str | None) -> str:
    """Normalize a model string returned by a NAD receiver."""
    if not model:
        return MODEL_AUTO
    normalized = model.upper().replace("-", "").replace("_", "").strip()
    compact = normalized.replace(" ", "")
    for profile in MODEL_PROFILES.values():
        names = (profile.model, *profile.aliases)
        for name in names:
            if compact == name.upper().replace("-", "").replace("_", "").replace(" ", ""):
                return profile.model
    return model.strip()


def profile_for_model(model: str | None) -> ModelProfile:
    """Return the best static profile for a model."""
    normalized = normalize_model(model)
    return MODEL_PROFILES.get(normalized, MODEL_PROFILES[MODEL_AUTO])


def model_query_variables(model: str | None, query_all: bool) -> list[str]:
    """Return queryable variables worth probing for a model."""
    if query_all:
        return sorted(QUERYABLE_VARIABLES)
    profile = profile_for_model(model)
    candidates = sorted(profile.core_variables)
    return sorted(variable for variable in candidates if profile.allows_variable(variable))


def possible_model_variables(model: str | None) -> list[str]:
    """Return protocol variables that are possible for the configured model."""
    profile = profile_for_model(model)
    variables = [
        variable
        for variable, meta in COMMANDS.items()
        if profile.allows_variable(variable)
        and (
            profile.model == MODEL_AUTO
            or profile.model == "T758"
            or profile.model in meta.get("models", [])
        )
    ]
    return sorted(variables)
