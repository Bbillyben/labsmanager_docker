from django.apps import AppConfig


class StaffConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'staff'

    def ready(self):
        # Register django-invitations' acceptance receiver before provisioning.
        from invitations import views  # noqa: F401
        from . import invitation_signals  # noqa: F401
