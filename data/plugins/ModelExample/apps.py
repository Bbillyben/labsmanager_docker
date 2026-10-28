"""Stable Django application identity for ModelExample."""

from django.apps import AppConfig


class ModelExampleConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "plugins.ModelExample"
    label = "model_example"
    verbose_name = "Model Example"
