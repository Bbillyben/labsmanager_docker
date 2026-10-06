from django.core.management.base import BaseCommand
from leave.tasks import pull_vacation_file

class Command(BaseCommand):
    help = 'update files from french gov api'
    
    def handle(self, *args, **options):
        pull_vacation_file()