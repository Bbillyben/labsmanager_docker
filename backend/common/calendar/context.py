"""Typed context passed to calendar domains and plugins."""

from dataclasses import dataclass, field
from datetime import date, datetime
from enum import Enum
from typing import Any, Mapping


class CalendarType(str, Enum):
    """Supported LabsManager calendar scopes."""

    MAIN = "main"
    TEAM = "team"
    EMPLOYEE = "employee"
    EMPLOYEE_GANTT = "employee-gantt"
    PROJECT = "project"
    PROJECT_ALL = "project_all"
    EMPLOYEE_PROJECT = "employee_project"

    @classmethod
    def from_value(cls, value):
        """Return a known type, falling back to the main calendar."""
        try:
            return cls(value)
        except (TypeError, ValueError):
            return cls.MAIN


@dataclass(frozen=True)
class CalendarContext:
    """Bounded request context independent from HTTP and plugin packages."""

    calendar_type: CalendarType
    user: Any
    start: date | datetime | None = None
    end: date | datetime | None = None
    employee_id: int | None = None
    project_id: int | None = None
    team_id: int | None = None
    filters: Mapping[str, Any] = field(default_factory=dict)
