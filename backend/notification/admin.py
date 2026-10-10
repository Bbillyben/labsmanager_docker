from django.contrib import admin, messages
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from .models import UserNotification


@admin.register(UserNotification)
class UserNotificationAdmin(admin.ModelAdmin):

    list_display = (
        'source_content_type',
        'source_object',
        'user',
        'action_type',
        'creation',
        'send',
        'is_done',
    )

    actions = ['mark_as_sent']

    @admin.display(boolean=True, description='Done')
    def is_done(self, obj):
        return obj.done

    @admin.action(description=_("Mark selected notifications as sent"))
    def mark_as_sent(self, request, queryset):
        updated = queryset.filter(send__isnull=True).update(
            send=timezone.now()
        )

        self.message_user(
            request,
            _("%(count)d notification(s) marked as sent.") % {
                'count': updated
            },
            level=messages.SUCCESS,
        )