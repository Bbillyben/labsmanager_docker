from django.http import Http404
from django.db import transaction
from rest_framework import permissions
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView

from .preferences import list_user_favorites, preference_status, resolve_preference_object, set_preference


class ObjectPreferenceV1View(APIView):
    permission_classes = (permissions.IsAuthenticated,)

    def object(self, request, type_name, object_id):
        try:
            return resolve_preference_object(request.user, type_name, object_id)
        except KeyError as error:
            raise Http404 from error

    def get(self, request, type_name, object_id):
        return Response(preference_status(request.user, self.object(request, type_name, object_id)))

    def put(self, request, type_name, object_id):
        obj = self.object(request, type_name, object_id)
        if not request.data or set(request.data) - {"favorite", "subscription"}:
            raise ValidationError({"detail": "Expected favorite and/or subscription."})
        if any(not isinstance(value, bool) for value in request.data.values()):
            raise ValidationError({"detail": "Preference values must be boolean."})
        with transaction.atomic():
            status = None
            for kind, enabled in request.data.items():
                status = set_preference(request.user, obj, kind, enabled)
        return Response(status)


class FavoriteNavigationV1View(APIView):
    permission_classes = (permissions.IsAuthenticated,)

    def get(self, request):
        return Response([{key: row[key] for key in ("type", "group", "id", "label", "url", "legacy")}
                         for row in list_user_favorites(request.user)])
