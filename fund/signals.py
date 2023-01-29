from fund.models import Fund, Fund_Item
from fund.apps import FundConfig
from django.db.models.signals import post_save, post_migrate
from django.dispatch import receiver
from expense.apps import ExpenseConfig
import logging
logger = logging.getLogger('labsmanager')

@receiver(post_save, sender=Fund_Item)
def save_Fund_Item_handler(sender, instance, **kwargs):
    logger.debug('[save_Fund_Item_handler] called')
    instance.fund.calculate()
    
# @receiver(post_migrate)
# def update_all_fund(sender, **kwargs):
#     print('Receiver - post_migrate : update_all_fund :'+str(sender))
#     # print(' - kwargs:'+str(kwargs))
#     if type(sender) == FundConfig:
#         fu=Fund.objects.all()
#         for f in fu:
#             f.calculate()
    