from django.core.management.base import BaseCommand, CommandError
import logging
logger = logging.getLogger('labsmanager')

from reports.models import ProjectWordReport, EmployeeWordReport
class Command(BaseCommand):
    help = 'Update Default file as default report template file'
    
    def add_arguments(self, parser):
        # Named (optional) arguments
        parser.add_argument(
            '--force',
            action='force_update',
            help='Force update of files and models',
        )
    
    def handle(self, *args, **options):
        logger.debug("COMMAND update_default called")
        logger.debug("  - start Project Report")
        rep = ProjectWordReport.objects.all()
        
        if rep is None:
            logger.debug("  No Project Report saved ")
            reP = ProjectWordReport()
            
         