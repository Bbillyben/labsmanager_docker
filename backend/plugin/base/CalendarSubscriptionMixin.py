"""Opt-in consumer of the published-calendar contract."""


class CalendarSubscriptionMixin:
    subscription_format = None

    class MixinMeta:
        MIXIN_NAME = "Calendar subscriptions"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.add_mixin("calendarsubscription", True, __class__)

    def create_published_subscription(self, request, provider_slug, calendar_id):
        """Return a one-time personal URL using the authenticated public request."""
        raise NotImplementedError

    def subscription_available(self):
        """Whether the consumer can currently serve the advertised format."""
        return True
