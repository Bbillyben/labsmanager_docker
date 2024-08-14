from expense.models import Expense_point, Expense
from django.db.models.signals import post_save
from django.dispatch import receiver

from settings.models import LMProjectSetting
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

from expense.models import exp_postsave
@receiver(exp_postsave) # signals dispatch on save by Expense and child classes
def save_expense_handler(sender, instance, **kwargs):
    logger.debug('[save_expense_handler] called')
    
    # get project setting
    proj = instance.fund_item.project
    proj_set=LMProjectSetting.get_setting('EXPENSE_CALCULATION', project=proj)
    if proj_set =="s":
        logger.debug(f" project {proj} settings {proj_set} is not in expense computational")
        return
    logger.debug(f" project {proj} settings {proj_set} START Compute, exp type : {instance.type}")
    instance.fund_item.calculate_expense(force=False, exp_type=instance.type)
     