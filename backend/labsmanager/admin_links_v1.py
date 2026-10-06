"""Object-scoped Django Admin change links for authenticated API responses."""

from django.urls import NoReverseMatch, reverse
from rest_framework import serializers


def get_admin_change_url(user, obj):
    """Return a resolvable change URL only for an authorized Admin user."""
    if not user or not user.is_authenticated or not obj or obj.pk is None:
        return None
    if not user.is_superuser:
        if not user.is_staff:
            return None
        permission = f"{obj._meta.app_label}.change_{obj._meta.model_name}"
        if not user.has_perm(permission, obj):
            return None
    try:
        return reverse(f"admin:{obj._meta.app_label}_{obj._meta.model_name}_change", args=[obj.pk])
    except NoReverseMatch:
        return None


class AdminUrlSerializerMixin(serializers.Serializer):
    """Shared read field for model serializers with a request context."""

    admin_url = serializers.SerializerMethodField()

    def get_admin_url(self, obj):
        request = self.context.get("request")
        return get_admin_change_url(request.user, obj) if request else None
