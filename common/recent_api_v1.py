"""Explicit recent destination tracking and visibility-scoped reads."""

from django.db import transaction
from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import RecentItem
from .recent_items import OBJECT_IDS, PAGE_IDS, resolve_recent_destination


class RecentItemsV1View(APIView):
    permission_classes = (permissions.IsAuthenticated,)

    def get(self, request):
        results = []
        for item in RecentItem.objects.filter(user=request.user).order_by("-last_viewed_at", "-pk")[:24]:
            destination = resolve_recent_destination(request.user, item.url_id, item.obj_id)
            if destination is not None:
                results.append({"url_id": item.url_id, "obj_id": item.obj_id,
                                **destination, "last_viewed_at": item.last_viewed_at})
            if len(results) == 6:
                break
        return Response(results)

    def post(self, request):
        data = request.data
        if not isinstance(data, dict) or set(data) - {"url_id", "obj_id"}:
            return Response({"detail": "Invalid destination."}, status=status.HTTP_400_BAD_REQUEST)
        url_id = data.get("url_id")
        obj_id = data.get("obj_id")
        if not isinstance(url_id, str) or not (
            url_id in OBJECT_IDS and type(obj_id) is int and obj_id > 0 or
            url_id in PAGE_IDS and obj_id is None
        ):
            return Response({"detail": "Invalid destination."}, status=status.HTTP_400_BAD_REQUEST)
        destination = resolve_recent_destination(request.user, url_id, obj_id)
        if destination is None:
            return Response({"detail": "Destination unavailable."}, status=status.HTTP_404_NOT_FOUND)
        with transaction.atomic():
            item, created = RecentItem.objects.get_or_create(user=request.user, url_id=url_id, obj_id=obj_id)
            if not created:
                item.save(update_fields=["last_viewed_at"])
        return Response({"url_id": url_id, "obj_id": obj_id, **destination,
                         "last_viewed_at": item.last_viewed_at},
                        status=status.HTTP_201_CREATED if created else status.HTTP_200_OK)
