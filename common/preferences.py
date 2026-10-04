"""Shared, visibility-scoped access to the historical generic preferences."""

from dataclasses import dataclass
from functools import lru_cache

from django.contrib.contenttypes.models import ContentType
from django.db import transaction
from django.shortcuts import get_object_or_404
from django.urls import reverse

from .models import favorite, subscription


@dataclass(frozen=True)
class PreferenceType:
    model: type
    group: str
    react_path: str | None = None


@lru_cache(maxsize=1)
def preference_types():
    # Import lazily: Project and Fund models import common elsewhere.
    from fund.models import Fund_Institution
    from project.models import Institution, Project
    from staff.models import Employee, Team

    return {
        "project": PreferenceType(Project, "projects", "/projects/{id}"),
        "employee": PreferenceType(Employee, "employees", "/employees/{id}"),
        "team": PreferenceType(Team, "teams", "/teams/{id}"),
        "institution": PreferenceType(Institution, "institutions", "/organizations/institutions/{id}"),
        "fund_institution": PreferenceType(Fund_Institution, "institutions", "/organizations/funders/{id}"),
    }


def visible_objects(user, type_name, queryset=None):
    spec = preference_types()[type_name]
    queryset = queryset if queryset is not None else spec.model.objects.all()
    if type_name == "team":
        from staff.team_api_v1 import visible_teams
        return visible_teams(user, queryset)
    if type_name in ("institution", "fund_institution"):
        return queryset if user.has_perm("common.display_infos") else queryset.none()
    scoped = spec.model.get_instances_for_user("view", user, queryset)
    # Project's historical helper resets an empty input queryset to all objects.
    return scoped.filter(pk__in=queryset.values("pk"))


def resolve_preference_object(user, type_name, object_id):
    if type_name not in preference_types():
        raise KeyError(type_name)
    return get_object_or_404(visible_objects(user, type_name), pk=object_id)


def type_for_content_type(content_type):
    for name, spec in preference_types().items():
        if (spec.model._meta.app_label, spec.model._meta.model_name) == (content_type.app_label, content_type.model):
            return name
    raise KeyError(f"{content_type.app_label}.{content_type.model}")


def preference_status(user, obj):
    content_type = ContentType.objects.get_for_model(obj)
    lookup = {"user": user, "content_type": content_type, "object_id": obj.pk}
    return {"favorite": favorite.objects.filter(**lookup).exists(),
            "subscription": subscription.objects.filter(**lookup).exists()}


def set_preference(user, obj, kind, enabled):
    if kind not in ("favorite", "subscription") or not isinstance(enabled, bool):
        raise ValueError("Invalid preference")
    model = favorite if kind == "favorite" else subscription
    lookup = {"user": user, "content_type": ContentType.objects.get_for_model(obj), "object_id": obj.pk}
    with transaction.atomic():
        if enabled:
            model.objects.get_or_create(**lookup)
        else:
            for relation in model.objects.filter(**lookup):
                relation.delete()
    return preference_status(user, obj)


def legacy_object_url(type_name, object_id):
    if type_name == "project":
        return reverse("project_single", args=[object_id])
    if type_name == "employee":
        return reverse("employee", args=[object_id])
    if type_name == "team":
        return reverse("team_single", args=[object_id])
    spec = preference_types()[type_name]
    return reverse("orga_single", kwargs={"pk": object_id, "app": spec.model._meta.app_label, "model": spec.model._meta.model_name})


def list_user_favorites(user):
    """Resolve each supported type in one scoped query; retain hidden relations."""
    return _list_user_relations(user, favorite)


def list_user_subscriptions(user):
    """Expose visible subscriptions through the same R2.21 scope and URLs."""
    return _list_user_relations(user, subscription)


def _list_user_relations(user, model):
    specs = preference_types()
    visible = visible_user_relations(user, model)
    result = []
    for name, _relation, obj in visible:
        spec = specs[name]
        result.append({
            "type": name, "group": spec.group, "id": obj.pk, "label": str(obj),
            "url": spec.react_path.format(id=obj.pk) if spec.react_path else legacy_object_url(name, obj.pk),
            "legacy_url": legacy_object_url(name, obj.pk),
            "legacy_group": str(spec.model._meta.verbose_name).title(),
            "legacy": spec.react_path is None,
        })
    order = {"projects": 0, "employees": 1, "teams": 2, "institutions": 3}
    return sorted(result, key=lambda row: (order[row["group"]], row["label"].casefold(), row["type"], row["id"]))


def visible_user_relations(user, model):
    rows = list(model.objects.filter(user=user).select_related("content_type"))
    specs = preference_types()
    by_type = {name: [] for name in specs}
    for relation in rows:
        try:
            name = type_for_content_type(relation.content_type)
        except KeyError:
            continue
        by_type[name].append(relation)
    result = []
    for name, relations in by_type.items():
        if not relations:
            continue
        spec = specs[name]
        objects = {obj.pk: obj for obj in visible_objects(user, name, spec.model.objects.filter(pk__in=[row.object_id for row in relations]))}
        result.extend((name, row, objects[row.object_id]) for row in relations if row.object_id in objects)
    return result
