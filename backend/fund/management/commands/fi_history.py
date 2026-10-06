from django.core.management.base import BaseCommand, CommandError
import logging
logger = logging.getLogger('labsmanager')


from django.db.models import Q

from fund.models import Fund_Item
from fund.models import AmountHistory

class Command(BaseCommand):
    help = 'migrate the fund item point before any updates'
           
    
    def handle(self, *args, **options):
        self.stdout.write("COMMAND fi_history called", ending='')
        logger.debug("COMMAND fi_history called")

        
        fi=Fund_Item.objects.all()

        for e in fi:
            ah=AmountHistory(
                    content_object=e,
                    amount=e.amount,
                    value_date=e.value_date,  
                    delta= 0,             
                )
            ah.save()
    
                    
