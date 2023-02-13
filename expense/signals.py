from expense.models import Expense_point
from django.db.models.signals import post_save
from django.dispatch import receiver
import logging
logger = logging.getLogger('labsmanager')

@receiver(post_save, sender=Expense_point)
def save_Expense_point_handler(sender, instance, **kwargs):
    # print('[save_Expense_point_handler] called')
    # print('  - sender :'+str(sender))    
    # print('  - instance :'+str(instance))
    # print('         - instance.entry_date :'+str(instance.entry_date))
    # print('         - instance.value_date :'+str(instance.value_date))
    # print('         - instance.fund :'+str(instance.fund))
    # print('         - instance.type :'+str(instance.type))
    # print('         - instance.amount :'+str(instance.amount))
    # print('  - kwargs :'+str(kwargs))
    logger.debug('[save_Fund_Item_handler] called')
    instance.fund.calculate()