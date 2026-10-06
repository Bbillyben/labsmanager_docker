from django.core.management.base import BaseCommand, CommandError
from django.apps import apps
from django.db import models
from django.core.files.storage import default_storage
import os



from reports.models import TemplateReport
from django.apps import apps
from django.core.files.storage import default_storage
from django.core.files import File
import os

class Command(BaseCommand):
    help = 'Update file paths for models inheriting from TemplateReport'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Simulate running the command without making changes',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        
        for model in apps.get_models():
            if issubclass(model, TemplateReport) and model != TemplateReport:
                self.stdout.write(f"Processing model: {model.__name__}")
                self.process_model(model, dry_run)

    def process_model(self, model, dry_run):
        subdir = model.getSubdir()
        for instance in model.objects.all():
            if instance.template:
                self.update_file_path(instance, subdir, dry_run)

    def update_file_path(self, instance, subdir, dry_run):
        old_path = instance.template.name
        filename = os.path.basename(old_path)
        new_path = os.path.join('report', 'report_template', subdir, filename)

        # if old_path != new_path:
        if default_storage.exists(old_path):
            if not dry_run:
                with default_storage.open(old_path, 'rb') as file:
                    new_file = File(file, name=new_path)
                    instance.template = new_file
                    instance.save()

                if old_path != new_path:
                    default_storage.delete(old_path)

            self.stdout.write(self.style.SUCCESS(
                f"{'Would update' if dry_run else 'Updated'} template for {instance}: {old_path} -> {new_path}"
            ))
        else:
            self.stdout.write(self.style.WARNING(
                f"File not found: {old_path} for {instance}"
            ))
