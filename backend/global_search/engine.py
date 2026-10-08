"""Shared text matching, weighted scoring and visible provider counts."""

from django.db.models import Case, IntegerField, Q, Value, When
from django.utils.translation import gettext as _

from .contracts import SearchQuery
from .language import AndNode, GenericInfoNode, KeyNode, NotNode, OrNode, TextNode
from .registry import search_registry


def _grade(value, query):
    value, query = value.casefold(), query.casefold()
    if not value or not query:
        return 0
    if value == query:
        return 100
    if value.startswith(query):
        return 70
    return 30 if query in value else 0


def _match(provider, obj, user, query):
    axes = [(field, label, str(value)) for field in provider.fields
            for label, value in provider.search_values(obj, field, user) if value]
    if not axes:
        return 0, ""
    best_terms = []
    for term in query.free_text_terms:
        best = max(((field.weight * _grade(value, term) / 100, field, label, value)
                    for field, label, value in axes), key=lambda item: item[0])
        if best[0] == 0:
            return 0, ""
        best_terms.append(best)
    score = sum(item[0] for item in best_terms) / len(best_terms)
    reason = max(best_terms, key=lambda item: item[0])
    for field, label, value in axes:
        phrase_score = field.weight * _grade(value, query.raw_text) / 100
        if phrase_score > score:
            score, reason = phrase_score, (phrase_score, field, label, value)
    return score, f"{reason[2]}: {reason[3]}"


def _term_query(provider, term, lookup, user):
    combined = Q()
    found = False
    for field in provider.fields:
        condition = provider.field_query(field, term, lookup, user)
        if condition is not None:
            combined |= condition
            found = True
    return combined if found else None


def _candidate_rank(provider, query, user):
    weighted = []
    for field in provider.fields:
        for lookup, grade in (("iexact", 100), ("istartswith", 70), ("icontains", 30)):
            condition = provider.field_query(field, query.raw_text, lookup, user)
            if condition is not None:
                weighted.append((field.weight * grade // 100, condition))
    weighted.sort(key=lambda item: -item[0])
    return Case(*(When(condition, then=Value(weight)) for weight, condition in weighted),
                default=Value(0), output_field=IntegerField())


def _node_query(provider, node, user, provider_keys):
    """None means that this branch is outside the provider's declared axes."""
    if isinstance(node, TextNode):
        terms = (node.value,) if node.phrase else tuple(node.value.split())
        conditions = [_term_query(provider, term, "icontains", user) for term in terms]
        if not conditions or any(condition is None for condition in conditions):
            return None
        result = Q()
        for condition in conditions:
            result &= condition
        return result
    if isinstance(node, KeyNode):
        if node.key in provider_keys:
            return _node_query(provider, TextNode(node.value, node.phrase), user, provider_keys) if node.key == provider.key else None
        field = next((item for item in provider.fields if item.key == node.key), None)
        return provider.field_query(field, node.value, "icontains", user) if field else None
    if isinstance(node, GenericInfoNode):
        return provider.generic_info_query(node.type_name, node.value, user) if provider.supports_generic_info else None
    if isinstance(node, NotNode):
        child = _node_query(provider, node.child, user, provider_keys)
        return ~child if child is not None else None
    children = [_node_query(provider, child, user, provider_keys) for child in node.children]
    supported = [child for child in children if child is not None]
    if isinstance(node, AndNode):
        if len(supported) != len(children):
            return None
        result = Q()
        for child in supported:
            result &= child
        return result
    if not supported:
        return None
    result = Q(pk__in=[])
    for child in supported:
        result |= child
    return result


def _leaf_score(provider, obj, user, node, provider_keys):
    if isinstance(node, GenericInfoNode):
        values = [(name, value) for name, value in provider.generic_info_values(obj, user)
                  if name.casefold() == node.type_name.casefold() and value.casefold() == node.value.casefold()]
        weight = next((field.weight for field in provider.fields if field.key == "generic_info"), 50)
        return (weight, f"{values[0][0]}: {values[0][1]}") if values else (0, "")
    if isinstance(node, KeyNode) and node.key in provider_keys and node.key != provider.key:
        return 0, ""
    fields = provider.fields if isinstance(node, TextNode) or (isinstance(node, KeyNode) and node.key in provider_keys) else tuple(
        field for field in provider.fields if field.key == node.key)
    value = node.value
    if isinstance(node, TextNode) and not node.phrase or isinstance(node, KeyNode) and not node.phrase and node.key in provider_keys:
        terms = tuple(value.split())
    else:
        terms = (value,)
    axes = [(field, label, str(item)) for field in fields for label, item in provider.search_values(obj, field, user) if item]
    if not axes:
        return 0, ""
    best = []
    for term in terms:
        score, label, item = max(((field.weight * _grade(item, term) / 100, label, item)
                                  for field, label, item in axes), key=lambda entry: entry[0])
        if not score:
            return 0, ""
        best.append((score, label, item))
    score = sum(item[0] for item in best) / len(best)
    reason = max(best, key=lambda item: item[0])
    for field, label, item in axes:
        phrase_score = field.weight * _grade(item, value) / 100
        if phrase_score > score:
            score, reason = phrase_score, (phrase_score, label, item)
    return score, f"{reason[1]}: {reason[2]}"


def _node_score(provider, obj, user, node, provider_keys):
    if isinstance(node, (TextNode, KeyNode, GenericInfoNode)):
        return _leaf_score(provider, obj, user, node, provider_keys)
    if isinstance(node, NotNode):
        score, _ = _node_score(provider, obj, user, node.child, provider_keys)
        return (0, "") if score else (1, "")
    scored = [_node_score(provider, obj, user, child, provider_keys) for child in node.children]
    if isinstance(node, AndNode):
        if any(not score for score, _ in scored):
            return 0, ""
        positive = [(score, reason) for score, reason in scored if reason]
        return (sum(score for score, _ in positive) / len(positive), max(positive, key=lambda pair: pair[0])[1]) if positive else (1, "")
    return max(scored, key=lambda pair: pair[0], default=(0, ""))


def _positive_leaves(node):
    if isinstance(node, NotNode):
        return ()
    if isinstance(node, (TextNode, KeyNode, GenericInfoNode)):
        return (node,)
    return tuple(leaf for child in node.children for leaf in _positive_leaves(child))


def _leaf_rank(provider, leaf, user, provider_keys):
    if isinstance(leaf, GenericInfoNode):
        condition = _node_query(provider, leaf, user, provider_keys)
        weight = next((field.weight for field in provider.fields if field.key == "generic_info"), 50)
        return Case(When(condition, then=Value(weight)), default=Value(0), output_field=IntegerField()) if condition is not None else None
    if isinstance(leaf, KeyNode) and leaf.key in provider_keys and leaf.key != provider.key:
        return None
    fields = provider.fields if isinstance(leaf, TextNode) or leaf.key in provider_keys else tuple(
        field for field in provider.fields if field.key == leaf.key)
    weighted = []
    for field in fields:
        for lookup, grade in (("iexact", 100), ("istartswith", 70), ("icontains", 30)):
            condition = provider.field_query(field, leaf.value, lookup, user)
            if condition is not None:
                weighted.append((field.weight * grade // 100, condition))
    weighted.sort(key=lambda item: -item[0])
    return Case(*(When(condition, then=Value(weight)) for weight, condition in weighted),
                default=Value(0), output_field=IntegerField()) if weighted else None


def _applicable(provider, node, provider_keys):
    if isinstance(node, TextNode):
        return bool(provider.fields)
    if isinstance(node, KeyNode):
        return node.key == provider.key if node.key in provider_keys else any(
            field.key == node.key for field in provider.fields)
    if isinstance(node, GenericInfoNode):
        return provider.supports_generic_info
    if isinstance(node, NotNode):
        return _applicable(provider, node.child, provider_keys)
    checks = [_applicable(provider, child, provider_keys) for child in node.children]
    return all(checks) if isinstance(node, AndNode) else any(checks)


class SearchEngine:
    """Filter visible querysets in SQL; score a bounded, prefetched candidate set."""

    def __init__(self, registry=None):
        self.registry = registry or search_registry

    def search_provider(self, provider, user, query, limit):
        if not provider.fields:
            return [], 0
        queryset = provider.visible_queryset(user)
        for term in query.free_text_terms:
            condition = _term_query(provider, term, "icontains", user)
            if condition is None:
                return [], 0
            queryset = queryset.filter(condition)
        queryset = queryset.distinct()
        count = queryset.count()
        if not count:
            return [], 0
        candidates = queryset.annotate(_search_rank=_candidate_rank(provider, query, user)).order_by(
            "-_search_rank", "pk"
        )[:max(200, limit * 15)]
        scored = {}
        for obj in provider.prepare_candidates(list(candidates)):
            score, reason = _match(provider, obj, user, query)
            if score:
                result = provider.make_result(obj, score=score, match_reason=reason)
                previous = scored.get(result.object_id)
                if previous is None or previous.score < score:
                    scored[result.object_id] = result
        results = sorted(scored.values(), key=lambda item: (-item.score, item.title.casefold(), item.object_id))
        return results[:limit], count

    def search_provider_ast(self, provider, user, query, limit, provider_keys):
        condition = _node_query(provider, query.ast, user, provider_keys)
        if condition is None:
            return [], 0
        queryset = provider.visible_queryset(user).filter(condition).distinct()
        count = queryset.count()
        if not count:
            return [], 0
        ranking = [rank for leaf in _positive_leaves(query.ast)
                   if (rank := _leaf_rank(provider, leaf, user, provider_keys)) is not None]
        if ranking:
            score = ranking[0]
            for rank in ranking[1:]:
                score += rank
            queryset = queryset.annotate(_search_rank=score)
            queryset = queryset.order_by("-_search_rank", "pk")
        else:
            queryset = queryset.order_by("pk")
        scored = {}
        for obj in provider.prepare_candidates(list(queryset[:max(200, limit * 15)])):
            score, reason = _node_score(provider, obj, user, query.ast, provider_keys)
            if score:
                result = provider.make_result(obj, score=score, match_reason=reason or _("Excluded by query"))
                previous = scored.get(result.object_id)
                if previous is None or previous.score < score:
                    scored[result.object_id] = result
        results = sorted(scored.values(), key=lambda item: (-item.score, item.title.casefold(), item.object_id))
        return results[:limit], count

    def search_with_counts(self, user, query: SearchQuery, *, limit=20, per_provider=10):
        providers = self.registry.active(user)
        provider_keys = {item.key for item in providers}
        if query.provider_filter:
            providers = tuple(item for item in providers if item.key == query.provider_filter)
        if query.ast is not None:
            providers = tuple(item for item in providers if _applicable(item, query.ast, provider_keys))
        if not query.free_text_terms and query.ast is None:
            return [], {}
        results, counts = [], {}
        for provider in providers:
            provider_results = []
            count = 0
            for source in provider.search_variants():
                if query.ast is None:
                    items, source_count = self.search_provider(source, user, query, min(limit, per_provider))
                else:
                    items, source_count = self.search_provider_ast(source, user, query, min(limit, per_provider), provider_keys)
                provider_results.extend(items)
                count += source_count
            provider_results.sort(key=lambda item: (-item.score, item.title.casefold(), item.object_id))
            results.extend(provider_results[:min(limit, per_provider)])
            counts[provider.key] = count
        results.sort(key=lambda item: (-item.score, item.provider_key, item.title.casefold(), item.object_id))
        return results[:limit], counts

    def search(self, user, query: SearchQuery, *, limit=20, per_provider=10):
        return self.search_with_counts(user, query, limit=limit, per_provider=per_provider)[0]
