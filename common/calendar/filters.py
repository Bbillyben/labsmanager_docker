"""Normalized calendar filter contracts."""

from dataclasses import dataclass, field
from typing import Any, Iterable, Mapping


CALENDAR_FILTER_TYPES = frozenset(
    {"select", "checkbox", "radio", "input-text", "input-color"}
)


@dataclass(frozen=True)
class LabsManagerCalendarFilterChoice:
    """One serializable choice exposed by a calendar filter."""

    value: Any
    label: str

    def as_dict(self):
        """Serialize the stable v1 representation."""
        return {"value": self.value, "label": self.label}


@dataclass(frozen=True)
class LabsManagerCalendarFilter:
    """A UI-neutral filter declared by a Calendar plugin."""

    id: str
    title: str
    type: str
    source: str
    choices: tuple[LabsManagerCalendarFilterChoice, ...] = field(default_factory=tuple)
    default: Any = None

    def __post_init__(self):
        if self.type not in CALENDAR_FILTER_TYPES:
            raise ValueError(f"Unsupported calendar filter type: {self.type}")

    @classmethod
    def from_definition(cls, *, filter_id, source, definition):
        """Build a normalized filter from one historical ``FILTERS`` entry."""
        choices = _normalize_choices(definition.get("choices", ()))
        return cls(
            id=filter_id,
            title=str(definition.get("title", filter_id)),
            type=definition["type"],
            source=source,
            choices=choices,
            default=definition.get("default"),
        )

    def as_dict(self):
        """Serialize the stable v1 representation."""
        return {
            "id": self.id,
            "title": self.title,
            "type": self.type,
            "source": self.source,
            "choices": [choice.as_dict() for choice in self.choices],
            "default": self.default,
        }


def _normalize_choices(values):
    """Accept mappings or iterable pairs without leaking plugin objects."""
    if values in (None, ""):
        return ()
    entries: Iterable
    if isinstance(values, Mapping):
        entries = values.items()
    else:
        entries = values
    try:
        return tuple(
            LabsManagerCalendarFilterChoice(value=value, label=str(label))
            for value, label in entries
        )
    except (TypeError, ValueError) as exc:
        raise ValueError("Calendar filter choices must be a mapping or pairs") from exc
