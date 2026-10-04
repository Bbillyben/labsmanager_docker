"""Contextual completion on the R3.11 tokenizer and active provider registry."""

from .language import completion_context
from .registry import search_registry


def utf16_to_index(source, offset):
    position = 0
    if offset == 0:
        return 0
    for index, char in enumerate(source, 1):
        position += 2 if ord(char) > 0xFFFF else 1
        if position == offset:
            return index
        if position > offset:
            break
    raise ValueError("Invalid cursor position")


def index_to_utf16(source, index):
    return sum(2 if ord(char) > 0xFFFF else 1 for char in source[:index])


def _quoted(value):
    return '"' + value.replace("\\", "\\\\").replace('"', '\\"') + '"'


def _ordered(values, prefix, limit):
    prefix = prefix.casefold()
    return sorted(values, key=lambda item: (not item["label"].casefold().startswith(prefix),
                                            item["label"].casefold(), item["kind"]))[:limit]


def autocomplete(user, query, cursor, *, provider_filter=None, limit=10, registry=None):
    registry = registry or search_registry
    active = registry.active(user)
    if provider_filter:
        active = tuple(provider for provider in active if provider.key == provider_filter)
    context = completion_context(query, cursor)
    suggestions = []
    prefix = context.prefix.casefold()
    if context.kind == "key":
        leading = " " if context.replace_start and not query[context.replace_start - 1].isspace() and query[context.replace_start - 1] != "(" else ""
        for provider in active:
            suggestions.append({"kind": "provider", "label": provider.key, "insert_text": f"{leading}{provider.key}:",
                                "detail": str(provider.label)})
        fields = {}
        for provider in active:
            for field in provider.fields:
                fields.setdefault(field.key, {"label": str(field.label), "providers": []})["providers"].append(str(provider.label))
        provider_keys = {provider.key for provider in active}
        for key, details in fields.items():
            if key in provider_keys:
                continue
            suggestions.append({"kind": "field", "label": key, "insert_text": f"{leading}{key}:",
                                "detail": f"{details['label']} — {', '.join(details['providers'])}"})
        if any(provider.supports_generic_info for provider in active):
            suggestions.append({"kind": "generic_info_type", "label": "info", "insert_text": f"{leading}info:", "detail": ""})
        suggestions = [item for item in suggestions if not prefix or prefix in item["label"].casefold()]
    elif context.kind == "operator":
        leading = "" if cursor and query[cursor - 1].isspace() else " "
        suggestions = [{"kind": "operator", "label": operator, "insert_text": f"{leading}{operator} ", "detail": ""}
                       for operator in ("AND", "OR")]
    elif context.kind == "generic_info_type":
        names = {}
        for provider in active:
            if provider.supports_generic_info:
                for name in provider.suggest_generic_info_types(user, context.prefix, limit):
                    names.setdefault(name.casefold(), name)
        suggestions = [{"kind": "generic_info_type", "label": name,
                        "insert_text": f"{_quoted(name)}=", "detail": ""} for name in names.values()]
    elif context.kind == "value":
        for provider in active:
            if context.key == provider.key and provider.autocomplete:
                for value in provider.suggest_provider_values(user, context.prefix, limit):
                    suggestions.append({"kind": "value", "label": value, "insert_text": _quoted(value),
                                        "detail": str(provider.label)})
            for field in provider.fields:
                if context.key == field.key and field.key in provider.suggestable_fields:
                    for value in provider.suggest_values(user, field, context.prefix, limit):
                        suggestions.append({"kind": "value", "label": value, "insert_text": _quoted(value),
                                            "detail": str(provider.label)})
    unique = {}
    for suggestion in suggestions:
        unique.setdefault((suggestion["kind"], suggestion["label"].casefold()), suggestion)
    suggestions = _ordered(unique.values(), context.prefix, limit)
    typed_value = query[context.replace_start:context.replace_end]
    info_value_incomplete = context.kind == "generic_info_value" and (
        not context.prefix or typed_value.startswith('"') and not typed_value.endswith('"'))
    return {"context": context.kind, "replace_start": context.replace_start,
            "replace_end": context.replace_end, "suggestions": suggestions,
            "incomplete": context.kind == "generic_info_type" or info_value_incomplete or
                          context.kind == "value" and not context.prefix}
