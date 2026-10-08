"""Stable contracts independent of the matching technology and Django models."""

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass(frozen=True)
class SearchQuery:
    raw_text: str
    free_text_terms: tuple[str, ...]
    provider_filter: str | None = None
    field_filters: dict[str, Any] = field(default_factory=dict)
    ast: Any = None

    @classmethod
    def from_text(cls, text: str, *, provider_filter: str | None = None):
        raw = " ".join(text.split())
        return cls(raw, tuple(raw.split()), provider_filter)


@dataclass(frozen=True)
class SearchResult:
    provider_key: str
    object_id: str
    title: str
    subtitle: str
    url: str
    score: float
    icon: str
    match_reason: str
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        if not all(isinstance(value, str) and value for value in
                   (self.provider_key, self.object_id, self.title, self.url, self.icon, self.match_reason)):
            raise ValueError("Search results require a provider, ID, title, URL, icon and match reason")
        if not self.url.startswith("/app/") or self.url.startswith("//"):
            raise ValueError("Search results need a React destination")
        if not isinstance(self.score, (int, float)) or self.score < 0:
            raise ValueError("Search result score must be nonnegative")

    def as_dict(self):
        return asdict(self)


@dataclass(frozen=True)
class SearchField:
    key: str
    label: str
    orm_paths: tuple[str, ...]
    type: str = "text"
    weight: int = 50

    def as_schema(self, *, suggest_values=False):
        return {"key": self.key, "label": str(self.label), "type": self.type,
                "operators": ["contains"], "suggest_values": suggest_values}


class SearchProvider:
    """One result type; providers own visibility, fields and React destinations."""

    key = ""
    label = ""
    icon = "Search"
    fields: tuple[SearchField, ...] = ()
    supports_generic_info = False
    autocomplete = False
    suggestable_fields: tuple[str, ...] = ()

    def available(self, user):
        return user.is_authenticated

    def visible_queryset(self, user):
        raise NotImplementedError

    def search_variants(self):
        """Concrete ORM sources represented by this one public result type."""
        return (self,)

    def prepare_candidates(self, candidates):
        return candidates

    def field_values(self, obj, search_field):
        return tuple(str(getattr(obj, path, "") or "") for path in search_field.orm_paths)

    def search_values(self, obj, search_field, user):
        """Return public (label, value) pairs for ranking and match reasons."""
        return tuple((str(search_field.label), value) for value in self.field_values(obj, search_field))

    def field_query(self, search_field, term, lookup, user):
        from django.db.models import Q
        if not search_field.orm_paths:
            return None
        condition = Q()
        for path in search_field.orm_paths:
            condition |= Q(**{f"{path}__{lookup}": term})
        return condition

    def generic_info_query(self, type_name, value, user):
        """Return a Q over parent IDs, or None when this provider has no GenericInfo."""
        return None

    def generic_info_values(self, obj, user):
        return ()

    def suggestion_values(self, obj, search_field, user):
        return tuple(value for _, value in self.search_values(obj, search_field, user))

    def suggest_values(self, user, search_field, prefix, limit):
        """Project only bounded, visible matching parents; never scan an unscoped model."""
        if search_field.key not in self.suggestable_fields or not prefix:
            return ()
        condition = self.field_query(search_field, prefix, "icontains", user)
        if condition is None:
            return ()
        values = {}
        candidates = self.visible_queryset(user).filter(condition).distinct().order_by("pk")[:max(100, limit * 20)]
        for obj in candidates:
            for value in self.suggestion_values(obj, search_field, user):
                value = str(value or "")
                if prefix.casefold() in value.casefold() and value.casefold() not in values:
                    values[value.casefold()] = value
        return tuple(sorted(values.values(), key=lambda value: (not value.casefold().startswith(prefix.casefold()), value.casefold()))[:limit])

    def suggest_provider_values(self, user, prefix, limit):
        """The first declared field is the provider's principal visible identity."""
        if not self.autocomplete or not self.fields or not prefix:
            return ()
        primary = self.fields[0]
        condition = self.field_query(primary, prefix, "icontains", user)
        if condition is None:
            return ()
        values = {}
        candidates = self.visible_queryset(user).filter(condition).distinct().order_by("pk")[:max(100, limit * 20)]
        for obj in candidates:
            for value in self.suggestion_values(obj, primary, user):
                value = str(value or "")
                if prefix.casefold() in value.casefold() and value.casefold() not in values:
                    values[value.casefold()] = value
        return tuple(sorted(values.values(), key=lambda value: (not value.casefold().startswith(prefix.casefold()), value.casefold()))[:limit])

    def suggest_generic_info_types(self, user, prefix, limit):
        return ()

    def make_result(self, obj, *, score, match_reason):
        raise NotImplementedError

    def schema(self):
        return {"key": self.key, "label": str(self.label), "icon": self.icon,
                "fields": [item.as_schema(suggest_values=item.key in self.suggestable_fields) for item in self.fields],
                "supports_generic_info": self.supports_generic_info,
                "autocomplete": self.autocomplete}
