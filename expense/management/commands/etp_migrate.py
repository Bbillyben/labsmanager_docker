from django.core.management.base import BaseCommand, CommandError
import logging
logger = logging.getLogger('labsmanager')


from django.db.models import Q

from expense.models import Expense_point
from fund.models import AmountHistory

class Command(BaseCommand):
    help = 'migrate the expense point before any updates'
    
    def add_arguments(self, parser):
        # Named (optional) arguments
        parser.add_argument(
            '--delete',
            action='store_true',
            help='Delete Expense Time point',
        )
        
        
    
    def handle(self, *args, **options):
        self.stdout.write("COMMAND etp_migrate called", ending='')
        logger.debug("COMMAND etp_migrate called")
        logger.debug(" use delete : "+str(options['delete']))
        result = input("this will delete all previous Expense Point, are you sure?")
        if not result[0].lower() == "y":
            logger.debug("aborting Expense Time POint Migration")
            return
        
        etp_no=Expense_point.last.all()
        etp_yes=Expense_point.objects.all().order_by("value_date")
    
        li={}
        for e in etp_yes:
            main=etp_no.filter(fund=e.fund, type=e.type).first()

            if not main:
                print(str(e)+" NOT FOUND IN MAIN")
            else:
                
                tid=str(str(e.fund)+"-"+str(e.type))
                vo=li.get(tid, 0)
                delta=e.amount-vo
                ah=AmountHistory(
                        content_object=main,
                        amount=e.amount,
                        value_date=e.value_date,  
                        delta= delta,             
                    )
                ah.save()
                li[tid]=e.amount
        
        if options['delete']:
            etp_yes=etp_yes.filter(~Q(pk__in=etp_no.values("pk")))
            etp_yes.delete()
                    
