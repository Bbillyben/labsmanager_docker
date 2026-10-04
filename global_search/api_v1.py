"""Authenticated Global Search and its live machine-readable provider schema."""

from rest_framework import permissions
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView

from .contracts import SearchQuery
from .autocomplete import autocomplete, index_to_utf16, utf16_to_index
from .engine import SearchEngine
from .language import SearchSyntaxError, TextNode, parse, tokenize, validate_keys
from .registry import search_registry


def _bounded_int(raw, name, *, default, maximum):
    if raw is None:
        return default
    try:
        value = int(raw)
    except (TypeError, ValueError):
        value = 0
    if str(value) != str(raw) or not 1 <= value <= maximum:
        raise ValidationError({name: f"Provide an integer from 1 to {maximum}."})
    return value


class SearchSchemaV1View(APIView):
    permission_classes = (permissions.IsAuthenticated,)

    def get(self, request):
        return Response({"providers": [item.schema() for item in search_registry.active(request.user)]})


class SearchAutocompleteV1View(APIView):
    permission_classes = (permissions.IsAuthenticated,)

    def get(self, request):
        raw = request.query_params.get("q", "")
        if len(raw) > 200:
            raise ValidationError({"q": "Query is too long."})
        try:
            cursor = int(request.query_params.get("cursor", len(raw)))
        except (TypeError, ValueError):
            raise ValidationError({"cursor": "Invalid cursor position."})
        try:
            cursor_index = utf16_to_index(raw, cursor)
        except ValueError:
            raise ValidationError({"cursor": "Cursor is outside the query."})
        limit = _bounded_int(request.query_params.get("limit"), "limit", default=10, maximum=12)
        provider_key = request.query_params.get("provider") or None
        if provider_key and search_registry.get(provider_key, request.user) is None:
            raise ValidationError({"provider": "Unknown or unavailable provider."})
        result = autocomplete(request.user, raw, cursor_index, provider_filter=provider_key, limit=limit)
        result["replace_start"] = index_to_utf16(raw, result["replace_start"])
        result["replace_end"] = index_to_utf16(raw, result["replace_end"])
        return Response(result)


class SearchV1View(APIView):
    permission_classes = (permissions.IsAuthenticated,)

    def get(self, request):
        raw = request.query_params.get("q", "")
        provider_key = request.query_params.get("provider") or None
        if len(raw) > 200:
            raise ValidationError({"q": "Query is too long."})
        try:
            ast = parse(raw)
            active_providers = search_registry.active(request.user)
            if ast is not None:
                validate_keys(ast, active_providers)
            if sum(token.kind in ("WORD", "STRING") for token in tokenize(raw)) > 12:
                raise SearchSyntaxError("Too many terms", 0)
        except SearchSyntaxError as error:
            return Response({"error": "invalid_search_query", "message": str(error),
                             "position": error.position, "expected": error.expected}, status=400)
        query = SearchQuery.from_text(raw, provider_filter=provider_key)
        if ast is not None and not (isinstance(ast, TextNode) and not ast.phrase):
            query = SearchQuery(raw, query.free_text_terms, provider_key, ast=ast)
        limit = _bounded_int(request.query_params.get("limit"), "limit", default=20, maximum=100)
        per_provider = _bounded_int(request.query_params.get("per_provider"), "per_provider", default=10, maximum=25)
        if provider_key and search_registry.get(provider_key, request.user) is None:
            raise ValidationError({"provider": "Unknown or unavailable provider."})
        results, counts = SearchEngine().search_with_counts(request.user, query, limit=limit, per_provider=per_provider)
        groups = {}
        for item in results:
            groups[item.provider_key] = groups.get(item.provider_key, 0) + 1
        return Response({"query": query.raw_text, "results": [item.as_dict() for item in results],
                         "groups": groups, "counts": counts})
