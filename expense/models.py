from pyexpat import model
from statistics import mode
from django.db import models
from django.utils.translation import gettext_lazy as _
from fund.models import Fund, Cost_Type, Fund_Item
from staff.models import Employee
from django.db.models import Q, Sum

from labsmanager.models_utils import PERCENTAGE_VALIDATOR, NEGATIVE_VALIDATOR    
from labsmanager.manager import LastInManager
from settings.models import LMUserSetting
from dashboard import utils
from auditlog.models import AuditlogHistoryField
from auditlog.registry import auditlog

from labsmanager.mixin import DateMixin

# Create your models here.
class Expense(models.Model):
    class Meta:
        """Metaclass defines extra model properties"""
        verbose_name = _("Expense")
        
    date = models.DateField(null=False, blank=False, verbose_name=_('Expense Date'))
    type = models.ForeignKey(Cost_Type, on_delete=models.CASCADE, verbose_name=_('Type'))
    amount=models.DecimalField(max_digits=12, decimal_places=2, verbose_name=_('Amount'))
    status_mod=(("e",_("Engaged")), 
                ("r", _("Realised")),
                ("p", _("Projected")),
                )
    status= models.CharField(
        max_length=1,
        choices=status_mod,
        blank=False,
        default='e', verbose_name=_('Status'),
    )
    fund_item = models.ForeignKey(Fund, on_delete=models.CASCADE, verbose_name=_('Related Fund'), related_name='tot_expense')
    history = AuditlogHistoryField()
    
    def __str__(self):
        return f'{self.fund_item.__str__()}/{self.type}'


class Contract_expense(Expense):
    class Meta:
        """Metaclass defines extra model properties"""
        verbose_name = _("Contract Expense")
    contract= models.ForeignKey('Contract', on_delete=models.CASCADE, verbose_name=_('Related Contract'))
    

class Expense_point(models.Model):
    class Meta:
        verbose_name = _("Total Expense Timepoint")
        unique_together = ('value_date', 'fund', 'type')

    entry_date = models.DateField(null=False, blank=False, verbose_name=_('Entry Date'))
    value_date = models.DateField(null=False, blank=False, verbose_name=_('value Date'))
    fund=models.ForeignKey(Fund, on_delete=models.CASCADE, verbose_name=_('Related Fund'))
    type = models.ForeignKey(Cost_Type, on_delete=models.CASCADE, verbose_name=_('Type'))
    amount=models.DecimalField(max_digits=12, decimal_places=2, verbose_name=_('Amount'), validators=NEGATIVE_VALIDATOR,)
    history = AuditlogHistoryField()
    
    # manager
    objects = models.Manager()
    last = LastInManager()
    
    def clean_amount(self):
        if self.cleaned_data['amount']>0:
            self.cleaned_data['amount']=-self.cleaned_data['amount']
        return self.cleaned_data['amount']
    
    @classmethod
    def get_lastpoint_by_fund(self, fundPk):
        # get cost type
        cts=Cost_Type.objects.all()
        bp = []
        for ct in cts:
            bpT=Expense_point.objects.filter(type=ct.pk, fund=fundPk).order_by('-value_date').first()
            if bpT:
                bp.append(bpT)
        return bp
    
    @classmethod
    def get_lastpoint_by_fund_qs(cls, ExpensePointItems):
        # get cost type
        cts=Cost_Type.objects.all().values('pk')
        bp = Expense_point.objects.none()
        for ct in cts:
            bpT=ExpensePointItems.filter(type=ct['pk']).order_by('-value_date').first()
            if bpT:
                bp= bp.union(ExpensePointItems.filter(pk=bpT.pk))
        return bp 
        
        
        
    
    def __str__(self):
        return f'{self.fund.__str__()}/{self.type} - {self.value_date}'
    
    
class Contract_type(models.Model):
    class Meta:
        verbose_name = _("Contract Type")
        ordering = ['name']
    name = models.CharField(max_length=60, verbose_name=_('Type name'))
    
    def __str__(self):
        return f'{self.name}'
    
class Contract(DateMixin):
    class Meta:
        """Metaclass defines extra model properties"""
        verbose_name = _("Contract")
        
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, verbose_name=_('Employee'))
    quotity = models.DecimalField(max_digits=4, decimal_places=3, default=0, validators=PERCENTAGE_VALIDATOR, verbose_name=_('Time quotity'))
    fund=models.ForeignKey(Fund, on_delete=models.CASCADE, verbose_name=_('Related Fund'))
    contract_type=models.ForeignKey(Contract_type,null=True, on_delete=models.SET_NULL, verbose_name=_('Contract Type'))
    is_active=models.BooleanField(default=True, verbose_name=_('is Active'))
    history = AuditlogHistoryField()
    
    def __str__(self):
        return f'{self.employee.__str__()} - {self.fund.__str__()}'
    
    @property
    def total_amount(self):
        exp = Contract_expense.objects.filter(contract=self.pk)
        if exp:
            return exp.aggregate(Sum('amount'))["amount__sum"]
        return 0
    
    @classmethod
    def staleFilter(cls):
        monthToGo=LMUserSetting.get_setting('DASHBOARD_CONTRACT_STALE_TO_MONTH')
        maxDate=utils.getDateToStale(monthToGo)
        return (Q(is_active=True) & Q(end_date__lte=maxDate))
    
    
auditlog.register(Expense)
auditlog.register(Contract_expense)
auditlog.register(Contract)
auditlog.register(Expense_point)