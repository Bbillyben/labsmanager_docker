"""Opt-in consumer of the published-calendar contract."""


class CalendarSubscriptionMixin:
    """Advertise a subscription format for published calendars.

    Consumers are discovered by ``subscription_format``. The core selects a
    consumer only when exactly one active plugin advertises an available format.
    Providers do not depend on a particular consumer implementation.
    """

    subscription_format = None

    class MixinMeta:
        MIXIN_NAME = "Calendar subscriptions"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.add_mixin("calendarsubscription", True, __class__)

    def create_published_subscription(self, request, provider_slug, calendar_id):
        """Create a personal subscription URL for a provider calendar.

        Args:
            request: Authenticated request used to identify the token owner.
            provider_slug: Technical identifier of the calendar provider.
            calendar_id: Identifier local to that provider.

        Returns:
            A response value for the subscription API. The ICS consumer
            returns a dictionary containing the generated ``url``.

        Raises:
            NotImplementedError: The consumer has not supplied this operation.
        """
        raise NotImplementedError

    def subscription_available(self):
        """Return whether this consumer can serve its advertised format."""
        return True
