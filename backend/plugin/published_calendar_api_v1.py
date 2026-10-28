"""Generic calendar subscription capability for plugin UIs."""

from django.http import Http404
from rest_framework import permissions
from rest_framework.authentication import SessionAuthentication
from rest_framework.response import Response
from rest_framework.views import APIView

from plugin.published_calendars import get_calendar, subscription_consumer


class PublishedCalendarSubscriptions(APIView):
    authentication_classes = (SessionAuthentication,)
    permission_classes = (permissions.IsAuthenticated,)

    def get(self, request):
        return Response({"formats": ["ics"] if subscription_consumer("ics") else []},
                        headers={"Cache-Control": "private, no-store"})

    def post(self, request, provider_slug, calendar_id):
        get_calendar(request.user, provider_slug, calendar_id)
        consumer = subscription_consumer("ics")
        if consumer is None:
            raise Http404
        result = consumer.create_published_subscription(request, provider_slug, calendar_id)
        return Response(result, status=201, headers={"Cache-Control": "private, no-store"})
