from django.core.management.base import BaseCommand, CommandError
import logging
logger = logging.getLogger('labsmanager')


from django.db.models import Q
from fund.models import AmountHistory

class Command(BaseCommand):
    help = 'remove duplicate in AmountHistory'
    
    # def add_arguments(self, parser):
    #     # Named (optional) arguments
    #     parser.add_argument(
    #         '--force',
    #         action='store_true',
    #         help='Force Update clean',
    #     )
        
        
    
    def handle(self, *args, **options):
        logger.debug("COMMAND remove_duplicate CALLED")
        self.stdout.write("COMMAND remove_duplicate", ending='\n')
        unik=AmountHistory.objects.values('content_type','object_id', 'value_date', 'amount').distinct()
        logger.debug(f" {AmountHistory.objects.count()} object found and {unik.count()} unic entry found")
        
        for ah in unik:
            sel=AmountHistory.objects.filter(content_type=ah['content_type'], object_id=ah['object_id'], value_date=ah['value_date']).values_list('pk', flat=True)[1:]
            if sel.count()>0:
                AmountHistory.objects.filter(pk__in=sel).delete()
            #AmountHistory.objects.filter(pk__in=Email.objects.filter(email=email).values_list('id', flat=True)[1:]).delete()

                    
