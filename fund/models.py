from tabnanny import verbose
from django.db import models
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _
from django.db.models import Sum, Q, F


from project.models import Project, Institution, Participant

from labsmanager.mixin import LabsManagerBudgetMixin, LabsManagerFocusBudgetMixin, LabsManagerFocusTypeMixin,  ActiveDateMixin, CachedModelMixin, RightsCheckerMixin
from labsmanager.models_utils import PERCENTAGE_VALIDATOR 
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType

from mptt.models import MPTTModel, TreeForeignKey

from auditlog.models import AuditlogHistoryField
from auditlog.registry import auditlog

import datetime
import decimal

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
    in_focus = models.BooleanField(null=False, blank=False, default=True, verbose_name=_('In Focus'))
    is_hr = models.BooleanField(null=False, blank=False, default=False, verbose_name=_('Is Human Resources'))
    
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
    
class Fund_Item(LabsManagerBudgetMixin, LabsManagerFocusTypeMixin, CachedModelMixin, RightsCheckerMixin):
    class Meta:
        """Metaclass defines extra model properties"""
        verbose_name = _("Fund Line")
        unique_together = ('type', 'fund',)
        
    entry_date = models.DateField(null=False, blank=False, default=datetime.date.today, verbose_name=_('Entry Date'))
    value_date = models.DateField(null=False, blank=False, default=datetime.date.today, verbose_name=_('value Date'))
    # type=models.ForeignKey(Cost_Type, on_delete=models.CASCADE, verbose_name=_('Type'))
    fund=models.ForeignKey('Fund', on_delete=models.CASCADE, verbose_name=_('Related Fund'), related_name='fund_item')
    history = AuditlogHistoryField()
    
    cached_vars=["amount"]
    
    @classmethod
    def get_instances_for_user(cls,perm, user, queryset=None):
        qset = super().get_instances_for_user(perm, user, queryset)
        if qset:
            return qset
        if not queryset:
            queryset = cls.objects.all()
        query = Q(employee__user=user) & Q(status__in=cls.get_project_modder(perm)) if cls.get_project_modder(perm) else Q(employee__user=user)
        proj=Participant.objects.filter(query).values('project')
        queryset = queryset.filter(fund__project__in=proj)  
        return queryset


    def __str__(self):
        return f'{self.type.short_name} - {self.fund}'
    
    
    
class Fund(LabsManagerFocusBudgetMixin, ActiveDateMixin, RightsCheckerMixin):
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
    
    
    def get_advancement_ratio(self):
        if self.amount == 0:
            return "-"
        
        date_ratio = decimal.Decimal((datetime.datetime.now().date()-self.start_date) / (self.end_date-self.start_date))
        return abs(self.expense)/(self.amount*date_ratio)
    
    def calculate(self, force=False):
        logger.debug(f'[Fund]-calculate :{str(self)} / (force: {force})')
        from expense.models import Expense_point
        # get all fund_items
        fi= Fund_Item.objects.filter(fund=self.pk)
        if fi:
            self.amount= fi.aggregate(Sum('amount'))["amount__sum"]
            self.amount_f= fi.filter(type__in_focus=True).aggregate(Sum('amount'))["amount__sum"]
        else:
            self.amount=0
            self.amount_f=0
        
        exp=Expense_point.objects.filter(fund=self.pk) #.last.fund(self.pk)
        if exp:
            self.expense = exp.aggregate(Sum('amount'))["amount__sum"]
            self.expense_f = exp.filter(type__in_focus=True).aggregate(Sum('amount'))["amount__sum"]
        else:
            self.expense = 0

            
        self.save()
        
        # Update Fund_Item
        
        if force: # force to make expense calculation based on 0
            fi.update(expense=0) 
            
        for etp in exp:
            fiS=fi.filter(type=etp.type)
            if fiS:
                fiS.update(expense=etp.amount)  # update the corresponding Fund_item
                    
            else: # create a new one
                logger.debug(f'[Fund]- create {etp.type} Fund Item')
                fiS=Fund_Item(
                    type=etp.type,
                    fund=self,
                    amount=0,
                    expense=etp.amount
                )
                fiS.save()
        
    def calculate_expense(self, force=False, exp_type=None):
        from expense.models import Expense, Expense_point
        logger.debug(f'[Fund]-calculate_expense :{str(self)} / (force: {force}) / Expense Type :{exp_type}')
        
        if exp_type is None:
            qset = Expense.objects.filter(fund_item = self.pk)
        else:
            qset = Expense.objects.filter(fund_item = self.pk, type=exp_type)
            
        
        sum_type =  qset.values('type').annotate(total_amount=Sum('amount')).order_by('type')
        
        if force:
            # force the update to 0 all amount
            if exp_type is None:
                expTP = Expense_point.objects.filter(fund = self.pk)
            else:
                expTP = Expense_point.objects.filter(fund = self.pk, type=exp_type)
            expTP.update(amount=0) 
        
        for st in sum_type:
            logger.debug(f'sum type : {st["type"]}, of anmout :{st["total_amount"]}')
            ct = Cost_Type.objects.get(pk=st["type"])
            try:
                exp=Expense_point.objects.get(fund=self.pk, type=ct)
                exp.amount = -st["total_amount"]
                exp.save()
            except:
                exp=Expense_point.objects.create(
                    entry_date = datetime.date.today(),
                    value_date = datetime.date.today(),
                    fund = self, 
                    type=ct, 
                    amount = -st["total_amount"]     
                )
                
                         
        
    def clean_end_date(self):
        ## print("EXIT DATE CLEAN Fund Model :"+str(self.cleaned_data))
        if( self.end_date != None and (self.start_date == None or self.start_date > self.end_date)):
            raise ValidationError(_('Exit Date (%(end)s) should be later than entry date (%(start)s) ') % ({'end':self.end_date, 'start':self.start_date}))
        return self.end_date
    
    def get_available(self):
        from expense.models import Expense_point
        import pandas as pd
        
        fi =Fund_Item.objects.filter(fund=self.pk).values_list('fund__project__name', 'fund__funder__short_name','fund__institution__short_name', 'type__short_name', 'fund__end_date', 'amount')
        # exp=Expense_point.objects.filter(fund=self.pk)
        # exp=Expense_point.get_lastpoint_by_fund_qs(exp)
        exp=Expense_point.objects.filter(fund=pk).last.fund(self.pk)
        expI= exp.values_list('fund__project__name', 'fund__funder__short_name','fund__institution__short_name', 'type__short_name','fund__end_date', 'amount')
        u = fi.union(expI)
        cpd=pd.DataFrame.from_records(u, columns=['project', 'funder','institution', 'type','end_date', 'amount',])
        # cpd = cpd.groupby('type').sum()
        # print(cpd)
        return cpd        
    
    @classmethod
    def get_availables(cls, funds):
        from expense.models import Expense_point
        import pandas as pd
        fi =Fund_Item.objects.filter(fund__in=funds).values_list('fund__project__name', 'fund__funder__short_name','fund__institution__short_name', 'type__short_name', 'fund__end_date', 'amount')
        exp=Expense_point.objects.filter(fund__in=funds)   #.last.fund(funds)
        expI= exp.values_list('fund__project__name', 'fund__funder__short_name','fund__institution__short_name', 'type__short_name','fund__end_date', 'amount')
        u = fi.union(expI)
        cpd=pd.DataFrame.from_records(u, columns=['project', 'funder','institution', 'type','end_date', 'amount',])
        return [cpd,]
    
    @classmethod
    def get_instances_for_user(cls,perm, user, queryset=None):
        qset = super().get_instances_for_user(perm, user, queryset)
        if qset:
            return qset
        if not queryset:
            queryset = cls.objects.all()
        query = Q(employee__user=user) & Q(status__in=cls.get_project_modder(perm)) if cls.get_project_modder(perm) else Q(employee__user=user)
        proj=Participant.objects.filter(query).values('project')
        queryset = queryset.filter(project__in=proj)
        return queryset
        
        
    def __str__(self):
        return f'{self.project.name} | {self.funder.short_name} -> {self.institution.short_name}'

def calculate_fund(*arg):
        logger.debug('[calculate_fund] :'+str(arg))
        fuPk=arg[0]
        if not fuPk or not isinstance(fuPk, int) or fuPk<=0:
            raise KeyError(f'No Fund id submitted for calculate_project')
        pj=Fund.objects.get(pk=fuPk)
        if not pj:
            raise ValueError("No Project Found")
        pj.calculate()
        

class BudgetAbstract(models.Model, RightsCheckerMixin):
    class Meta:
        """Metaclass defines extra model properties"""
        verbose_name = _("BudgetAbstract")
        abstract = True
        
    cost_type=models.ForeignKey(Cost_Type, on_delete=models.SET_NULL, verbose_name=_('Type'), null=True)
    amount=models.DecimalField(max_digits=12, decimal_places=2, verbose_name=_('Amount'), default=0)
    fund=models.ForeignKey('Fund', on_delete=models.CASCADE, verbose_name=_('fund'))
    emp_type=models.ForeignKey('staff.Employee_Type', on_delete=models.SET_NULL, verbose_name=_('employee type'), null=True,blank=True)
    contract_type=models.ManyToManyField('expense.Contract_type', blank=True)
    employee=models.ForeignKey('staff.Employee', on_delete=models.SET_NULL, verbose_name=_('employee'), null=True,blank=True)
    quotity = models.DecimalField(max_digits=4, decimal_places=3, default=0, validators=PERCENTAGE_VALIDATOR, verbose_name=_('quotity'),  null=True,blank=True)
    desc = models.CharField(max_length=150, verbose_name=_('Description'), blank=True, null=True)
    history = AuditlogHistoryField()
    
    
    def clean(self, *args, **kwargs):
        ctRH =Cost_Type.objects.filter(is_hr=True).get_descendants(include_self=True)
        isIn=ctRH.filter(pk=self.cost_type.pk)
        
        # str =  ",  ".join([p.name for p in self.contract_type.all()])
        if isIn.count()==0 and (not self.emp_type is None or not self.employee is None): # or self.contract_type != None):
            raise ValidationError(_('Employee Type, Contract Type and employee can not be defined if Cost Type is not of RH or descendant '))
            
    def __str__(self):
        return f'{self.fund} | {self.cost_type.short_name} -> {self.amount}'
    
    @classmethod
    def get_instances_for_user(cls,perm, user, queryset=None):
        qset = super().get_instances_for_user(perm, user, queryset)
        if qset:
            return qset
        if not queryset:
            queryset = cls.objects.all()
        query = Q(employee__user=user) & Q(status__in=cls.get_project_modder(perm)) if cls.get_project_modder(perm) else Q(employee__user=user)
        proj=Participant.objects.filter(query).values('project')
        queryset = queryset.filter(fund__project__in=proj)
        return queryset
    

class Budget(BudgetAbstract):
    class Meta:
        verbose_name = _("Budget")
        
class Contribution(BudgetAbstract, ActiveDateMixin):
    class Meta:
        verbose_name = _("Contribution")
    
        
class AmountHistory(models.Model):
    content_type = models.ForeignKey(ContentType, related_name="content_type_amountHistory", on_delete=models.CASCADE, )
    object_id = models.PositiveIntegerField()
    content_object = GenericForeignKey('content_type', 'object_id')
    amount=models.DecimalField(max_digits=12, decimal_places=2, verbose_name=_('Amount'))
    delta=models.DecimalField(max_digits=12, decimal_places=2, default=0, verbose_name=_('Delta'))
    created_at = models.DateField(auto_now_add=True, null=False, blank=False, verbose_name=_('Date'))
    value_date = models.DateField(null=True, blank=True, verbose_name=_('Value Date'))
    
    
    class Meta:
        verbose_name = _("Amount History")

auditlog.register(Fund_Item)
auditlog.register(Fund)
auditlog.register(Budget)
auditlog.register(Contribution)