from django.core.management.base import BaseCommand, CommandError
import logging
logger = logging.getLogger('labsmanager')


from django.db.models import Q
from fund.models import Fund

class Command(BaseCommand):
    help = 'migrate the expense point before any updates'
    
    def add_arguments(self, parser):
        # Named (optional) arguments
        parser.add_argument(
            '--force',
            action='store_true',
            help='Force Update clean',
        )
        
        
    
    def handle(self, *args, **options):
        self.stdout.write("COMMAND update_fund called", ending='')
        force=options['force']
        fu=Fund.objects.all()
        for f in fu:
            f.calculate(force=force)
                    
