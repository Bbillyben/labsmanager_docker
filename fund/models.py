from tabnanny import verbose
from django.db import models
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _
from django.db.models import Sum, Q, F


from project.models import Project, Institution
from labsmanager.mixin import LabsManagerBudgetMixin, ActiveDateMixin

from mptt.models import MPTTModel, TreeForeignKey

from auditlog.models import AuditlogHistoryField
from auditlog.registry import auditlog

import logging
logger = logging.getLogger('labsmanager')

class Cost_Type(MPTTModel):
    class Meta:
        """Metaclass defines extra model properties"""
        verbose_name = _("Cost Type")
        # ordering = ['short_name']
    
    class MPTTMeta:
        order_insertion_by = ['short_name']
                
    parent = TreeForeignKey('self', on_delete=models.CASCADE, null=True, blank=True, related_name='children')
    short_name= models.CharField(max_length=10, verbose_name=_('Abbreviation'))
    name = models.CharField(max_length=60, verbose_name=_('Type name'))
    
    def __str__(self):
        return f'{self.name}'
    
class Fund_Institution(models.Model):
    class Meta:
        """Metaclass defines extra model properties"""
        verbose_name = _("Funder Institution")
        ordering = ['short_name']
        
    short_name= models.CharField(max_length=10, verbose_name=_('Funder abbreviation'))
    name = models.CharField(max_length=60, verbose_name=_('Funder Name'))
    
    def __str__(self):
        return f'{self.short_name}'
    
class Fund_Item(LabsManagerBudgetMixin):
    class Meta:
        """Metaclass defines extra model properties"""
        verbose_name = _("Fund Line")
        unique_together = ('type', 'fund',)
        
    type=models.ForeignKey(Cost_Type, on_delete=models.CASCADE, verbose_name=_('Type'))
    # amount=models.DecimalField(max_digits=12, decimal_places=2, verbose_name=_('Amount'))
    fund=models.ForeignKey('Fund', on_delete=models.CASCADE, verbose_name=_('Related Fund'))
    history = AuditlogHistoryField()

    def __str__(self):
        return f'{self.type.short_name} - {self.fund}'
class Fund(LabsManagerBudgetMixin, ActiveDateMixin):
    class Meta:
        """Metaclass defines extra model properties"""
        verbose_name = _("Fund")
        ordering = ['project__name']
        constraints = [
            models.CheckConstraint(
                check=Q(end_date__gt=F('start_date')),
                name=_("End Date should be greater than start date"),
            )
        ]
    project=models.ForeignKey(Project, on_delete=models.CASCADE, verbose_name=_('Funded Project'))
    funder=models.ForeignKey(Fund_Institution, on_delete=models.CASCADE, verbose_name=_('Fund Instituition'))
    institution=models.ForeignKey(Institution, on_delete=models.CASCADE, verbose_name=_('Manager Institution'))
    ref= models.CharField(max_length=30, blank=True, verbose_name=_('Reference'))
    history = AuditlogHistoryField()
    
    @property
    def getId(self):
        return f'{self.project.name} | {self.funder.short_name} -> {self.institution.short_name}'
    
    def calculate(self):
        logger.debug('[Fund]-calculate :'+str(self))
        from expense.models import Expense_point
        # get all fund_items
        fi= Fund_Item.objects.filter(fund=self.pk)
        if fi:
            self.amount= fi.aggregate(Sum('amount'))["amount__sum"]
        else:
            self.amount=0
        
        # get all expense
        # exp=Expense_point.objects.filter(fund=self.pk)
        # exp=Expense_point.get_lastpoint_by_fund_qs(exp)
        exp=Expense_point.last.fund(self.pk)
        sumEP=0
        for etp in exp:
            sumEP+=etp.amount
            fiS=fi.filter(type=etp.type).update(expense=etp.amount)  # update the corresponding Fund_item
        self.expense=sumEP
        self.save()
    
    def clean_end_date(self):
        ## print("EXIT DATE CLEAN Fund Model :"+str(self.cleaned_data))
        if( self.end_date != None and (self.start_date == None or self.start_date > self.end_date)):
            raise ValidationError(_('Exit Date (%s) should be later than entry date (%s) ') % (self.end_date, self.start_date))
        return self.end_date
    
    def get_available(self):
        from expense.models import Expense_point
        import pandas as pd
        
        fi =Fund_Item.objects.filter(fund=self.pk).values_list('fund__project__name', 'fund__funder__short_name','fund__institution__short_name', 'type__short_name', 'fund__end_date', 'amount')
        # exp=Expense_point.objects.filter(fund=self.pk)
        # exp=Expense_point.get_lastpoint_by_fund_qs(exp)
        exp=Expense_point.last.fund(self.pk)
        expI= exp.values_list('fund__project__name', 'fund__funder__short_name','fund__institution__short_name', 'type__short_name','fund__end_date', 'amount')
        u = fi.union(expI)
        cpd=pd.DataFrame.from_records(u, columns=['project', 'funder','institution', 'type','end_date', 'amount',])
        # cpd = cpd.groupby('type').sum()
        # print(cpd)
        return cpd        
        
    def __str__(self):
        return f'{self.project.name} | {self.funder.short_name} -> {self.institution.short_name}'
    
auditlog.register(Fund_Item)
auditlog.register(Fund)