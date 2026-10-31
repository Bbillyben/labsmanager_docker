"""Normalized calendar event contract."""

from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Any, Mapping


def _iso(value):
    return value.isoformat() if isinstance(value, (date, datetime)) else value


@dataclass(frozen=True)
class LabsManagerCalendarEvent:
    """Non-persistent event shared by APIs, domains, and plugins.

    Plugins provide stable ``id`` values and mark their ``source`` and ``kind``.
    ``metadata`` may carry presentation details such as destinations or
    assignees; the core serializers copy it into the public event shape. The
    dataclass is frozen, so providers construct a replacement to change data.
    """

    id: str
    title: str
    start: date | datetime
    end: date | datetime | None = None
    source: str = "core"
    kind: str = "event"
    all_day: bool = True
    color: str | None = None
    description: str | None = None
    display: str = "auto"
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def as_dict(self):
        """Return the normalized v1 API shape with ISO date/time strings."""
        return {
            "id": self.id,
            "title": self.title,
            "start": _iso(self.start),
            "end": _iso(self.end),
            "source": self.source,
            "kind": self.kind,
            "all_day": self.all_day,
            "color": self.color,
            "description": self.description,
            "display": self.display,
            "metadata": dict(self.metadata),
        }

    def as_fullcalendar_dict(self):
        """Return the legacy FullCalendar shape with metadata in extendedProps."""
        event = {
            "id": self.id,
            "title": self.title,
            "start": _iso(self.start),
            "end": _iso(self.end),
            "display": self.display,
            "color": self.color,
            "desc": self.description,
            "extendedProps": {
                "source": self.source,
                "kind": self.kind,
                **dict(self.metadata),
            },
        }
        return {key: value for key, value in event.items() if value is not None}
