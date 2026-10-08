from django.apps import AppConfig


class DataConsistencyConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "data_consistency"

    def ready(self):
        from . import signals  # noqa: F401
