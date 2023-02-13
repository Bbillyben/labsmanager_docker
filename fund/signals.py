from fund.models import Fund, Fund_Item
from fund.apps import FundConfig
from django.db.models.signals import post_save, post_migrate, post_delete
from django.dispatch import receiver
from expense.apps import ExpenseConfig

from django_q.tasks import async_task, result

import logging
logger = logging.getLogger('labsmanager')

@receiver(post_save, sender=Fund_Item)
def save_Fund_Item_handler(sender, instance, **kwargs):
    logger.debug('[save_Fund_Item_handler] called')
    instance.fund.calculate()
    # async_task(
    #     'fund.models.calculate_fund',
    #     instance.fund.pk
    # )

@receiver(post_delete, sender=Fund_Item)
def delete_Fund_Item_handler(sender, instance, **kwargs):
    logger.debug('[Delete_Fund_Item_handler] called')
    instance.fund.calculate() 
    # async_task(
    #     'fund.models.calculate_fund',
    #     instance.fund.pk
    # )  


@receiver(post_save, sender=Fund)
def save_Fund_handler(sender, instance, **kwargs):
    logger.debug('[save_Fund_handler] called')
    instance.project.calculate()
    # async_task(
    #     'project.models.calculate_project',
    #     instance.project.pk
    # )
    
# @receiver(post_migrate)
# def update_all_fund(sender, **kwargs):
#     print('Receiver - post_migrate : update_all_fund :'+str(sender))
#     # print(' - kwargs:'+str(kwargs))
#     if type(sender) == FundConfig:
#         fu=Fund.objects.all()
#         for f in fu:
#             f.calculate()
    