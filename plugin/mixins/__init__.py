"""Utility file to enable simper imports."""

from plugin.base.SettingMixin import SettingsMixin
from plugin.base.ScheduleMixin import ScheduleMixin
from plugin.base.CalendarEventMixin import CalendarEventMixin
from plugin.base.MailSubscriptionMixin  import MailSubscriptionMixin
from plugin.base.ReportMixin  import ReportMixin
from plugin.base.UrlsMixin import UrlsMixin
from plugin.base.DashboardPluginMixin import DashboardPluginMixin
from plugin.base.SearchPluginMixin import SearchPluginMixin

__all__ = [
    'SettingsMixin',
    'ScheduleMixin',
    'MailSubscriptionMixin',
    'CalendarEventMixin',
    'ReportMixin',
    'UrlsMixin',
    'DashboardPluginMixin',
    'SearchPluginMixin',
]
