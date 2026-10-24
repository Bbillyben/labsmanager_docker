"""Detached worker entry point for one administrator-requested installation."""

from django.core.management.base import BaseCommand, CommandError

from plugin.dependencies import install


class Command(BaseCommand):
    help = "Execute one queued plugin dependency installation."

    def add_arguments(self, parser):
        parser.add_argument("plugin_key")
        parser.add_argument("operation_id")

    def handle(self, *args, **options):
        try:
            install(options["plugin_key"], options["operation_id"])
        except Exception as exc:
            raise CommandError(str(exc)) from exc
