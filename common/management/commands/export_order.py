from django.apps import apps
# from django.db.models import get_app, get_models
from django.core.management.base import BaseCommand, CommandError
import logging
logger = logging.getLogger('labsmanager')


class Command(BaseCommand):
    help = 'get export order for all models'
    ordered_model_names = [
        'app_name.Model1',
        'app_name.Model2',
        'app_name.Model3',
    ]
    
    
    def handle(self, *args, **options):
        logger.debug("COMMAND export_order called")            
        all_models = []
        for app_config in apps.get_app_configs():
            for model in app_config.get_models():
                all_models.append(f"{model._meta.app_label}.{model.__name__}")

            
        print(" ".join(all_models))
            