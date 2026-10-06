from django.core.management.base import BaseCommand, CommandError
import logging
logger = logging.getLogger('labsmanager')


from django.db.models import Q
from fund.models import AmountHistory

class Command(BaseCommand):
    help = 'Clean AmountHistory Instances'
    
    
    def handle(self, *args, **options):
        logger.debug("COMMAND clean_history CALLED")
        self.stdout.write("COMMAND clean_history", ending='\n')
        AHL=AmountHistory.objects.all() #values('content_type','object_id', 'value_date', 'amount')
        
        for ah in AHL:
            md_class=ah.content_type.model_class()
            ob=md_class.objects.filter(pk = ah.object_id)
            if ob.count()==0:
                 logger.debug(f"Clean Instance {ah.pk}, for model : {md_class} / id : {ah.object_id}")
                 rest = ah.delete()
                 logger.debug("Delete res : "+str(rest))
            #AmountHistory.objects.filter(pk__in=Email.objects.filter(email=email).values_list('id', flat=True)[1:]).delete()

                    
