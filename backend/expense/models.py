from pyexpat import model
from statistics import mode
from django.db import models
from django.utils.translation import gettext_lazy as _
from fund.models import Fund, Cost_Type, Fund_Item, Budget
from staff.models import Employee
from django.db.models import Exists, OuterRef, Q, Sum

from labsmanager.models_utils import PERCENTAGE_VALIDATOR, NEGATIVE_VALIDATOR    
from labsmanager.manager import LastInManager
from settings.models import LMUserSetting
from dashboard import utils
from auditlog.models import AuditlogHistoryField
from auditlog.registry import auditlog

from labsmanager.mixin import DateMixin, CachedModelMixin, CachedModelDispatchMixin, LabsManagerFocusTypeMixin, RightsCheckerMixin
from model_utils.managers import InheritanceManager

import django.dispatch

## signal to dispatch save
exp_postsave = django.dispatch.Signal()
class Expense(LabsManagerFocusTypeMixin, CachedModelMixin):
    
    """Individual spending record attached to a Fund and optional Budget."""
    object_inherit = InheritanceManager()
    
    class Meta:
        """Metaclass defines extra model properties"""
        verbose_name = _("Expense")
    
    expense_id = models.CharField(blank=True, null=True, verbose_name=_('Expense Id'))  
    desc = models.CharField(blank=True, null=True, verbose_name=_('Description'))   
    date = models.DateField(null=False, blank=False, verbose_name=_('Expense Date'))
    # type = models.ForeignKey(Cost_Type, on_delete=models.CASCADE, verbose_name=_('Type'))
    amount=models.DecimalField(max_digits=12, decimal_places=2, verbose_name=_('Amount'))
    status_mod=(("e",_("Engaged")), 
                ("r", _("Realised")),
                ("p", _("Projected")),
                )
    status= models.CharField(
        max_length=1,
        choices=status_mod,
        blank=False,
        default='r', verbose_name=_('Status'),
    )
    fund_item = models.ForeignKey(Fund, on_delete=models.CASCADE, verbose_name=_('Related Fund'), related_name='tot_expense')
    budget_item = models.ForeignKey(Budget, on_delete=models.CASCADE, verbose_name=_('Related Budget'), related_name='exp_budget', null=True, blank=True)
    
    
    cached_vars=["amount", "type","budget_item",]
    
    history = AuditlogHistoryField()
    
    def save(self, *args, **kwargs):
        """Persist an Expense and emit the legacy post-save signal.

                Notes:
                    Downstream receivers may recalculate Fund totals.
        """
        result = super().save(*args, **kwargs)
        exp_postsave.send(sender=self.__class__, instance=self)
        
    def __str__(self):
        return f'{self.fund_item.__str__()}/{self.type}'

class Contract_expense(Expense):
    """Expense attributed to a specific Contract."""
    class Meta:
        """Metaclass defines extra model properties"""
        verbose_name = _("Contract Expense")
    contract= models.ForeignKey('Contract', on_delete=models.CASCADE, verbose_name=_('Related Contract'))
    

class Expense_point(LabsManagerFocusTypeMixin, CachedModelDispatchMixin):
    """Cached total spending for one Fund and cost type."""
    class Meta:
        verbose_name = _("Total Expense Timepoint")
        unique_together = ('fund', 'type')

    entry_date = models.DateField(null=False, blank=False, verbose_name=_('Entry Date'))
    value_date = models.DateField(null=False, blank=False, verbose_name=_('value Date'))
    fund=models.ForeignKey(Fund, on_delete=models.CASCADE, verbose_name=_('Related Fund'))
    # type = models.ForeignKey(Cost_Type, on_delete=models.CASCADE, verbose_name=_('Type'))
    amount=models.DecimalField(max_digits=12, decimal_places=2, verbose_name=_('Amount'), validators=NEGATIVE_VALIDATOR,)
    history = AuditlogHistoryField()
    
    # manager
    objects = models.Manager()
    last = LastInManager()
    
    cached_vars=["amount"]
    
    def clean_amount(self):
        if self.cleaned_data['amount']>0:
            self.cleaned_data['amount']=-self.cleaned_data['amount']
        return self.cleaned_data['amount']
    
    @classmethod
    def get_lastpoint_by_fund(self, fundPk):
        # get cost type
        """Return the latest Expense point for each cost type in a Fund."""
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
        """Build a queryset containing the latest point per cost type."""
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
    """Category assigned to an Employee Contract."""
    class Meta:
        verbose_name = _("Contract Type")
        ordering = ['name']
    name = models.CharField(max_length=60, verbose_name=_('Type name'))
    
    def __str__(self):
        return f'{self.name}'

from .manager import effective_Manager, provisionnal_Manager
import decimal
class Contract(DateMixin, RightsCheckerMixin):
    """Dated employment allocation charged to a Fund."""
    objects = models.Manager()
    provisionnal = provisionnal_Manager()
    effective = effective_Manager()
    
    class Meta:
        """Metaclass defines extra model properties"""
        verbose_name = _("Contract")
        # default_manager_name = "objects"
        
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, verbose_name=_('Employee'))
    quotity = models.DecimalField(max_digits=4, decimal_places=3, default=1, validators=PERCENTAGE_VALIDATOR, verbose_name=_('Time quotity'))
    fund=models.ForeignKey(Fund, on_delete=models.CASCADE, verbose_name=_('Related Fund'))
    contract_type=models.ForeignKey(Contract_type,null=True, blank=True, on_delete=models.SET_NULL, verbose_name=_('Contract Type'))
    is_active=models.BooleanField(default=True, verbose_name=_('is Active'))
    
    type_cont=(("effe",_("Effective")), ("prov", _("Provisionnal")))
    status = models.CharField(
        max_length=4,
        choices=type_cont,
        blank=False,
        default='effe', 
        verbose_name=_('Status'),        
    )
    
    history = AuditlogHistoryField()
    
    def __str__(self):
        return f'{self.employee.__str__()} - {self.fund.__str__()} / {self.contract_type}'
    
    @property
    def total_amount(self):
        """Sum expenses attached to this Contract."""
        exp = Contract_expense.objects.filter(contract=self.pk)
        if exp:
            return exp.aggregate(Sum('amount'))["amount__sum"]
        return 0
    
    @property
    def remain_amount(self):
        """Estimate the amount associated with the remaining Contract period."""
        ratio = self.get_left_time_ratio()
        amount = self.total_amount
        if ratio != "-" and amount:
            return decimal.Decimal(ratio)*amount
        return 0
    
    @property
    def man_month(self):
        """Calculate Contract duration in months weighted by its workload share."""
        if not self.start_date or not self.end_date or not self.quotity:
            return 0
        return ((self.end_date.year - self.start_date.year) * 12 + self.end_date.month - self.start_date.month)*self.quotity
        
    
    @classmethod
    def staleFilter(cls):
        """Build a filter for active Contracts approaching their end date."""
        monthToGo=LMUserSetting.get_setting('DASHBOARD_CONTRACT_STALE_TO_MONTH')
        maxDate=utils.getDateToStale(monthToGo)
        return (Q(is_active=True) & Q(end_date__lte=maxDate))
    
    @classmethod
    def get_instances_for_user(cls,perm, user, queryset=None):
        """Filter Contracts through the caller's object-level access."""
        from project.models import Project, Participant
        from staff.models import Employee_Superior
        qset = super().get_instances_for_user(perm, user, queryset)
        if qset:
            return qset
        if queryset is None:
            queryset = cls.objects.all()

        if perm.lower() == 'view':
            # Match the union of the existing Employee and Project Contract scopes.
            employees = Employee.get_instances_for_user('view', user, Employee.objects.all()).values('pk')
            projects = Project.get_instances_for_user('view', user, Project.objects.all()).values('pk')
            funds = Fund.get_instances_for_user('view', user, Fund.objects.filter(project_id__in=projects)).values('pk')
            participant = Participant.objects.filter(
                project_id=OuterRef('fund__project_id'), employee_id=OuterRef('employee_id')
            )
            return queryset.alias(_project_contract_participant=Exists(participant)).filter(
                Q(employee_id__in=employees) |
                Q(fund_id__in=funds, _project_contract_participant=True)
            )
        
        subordinate = Employee_Superior.objects.filter(superior__user = user).values_list("employee", flat=True)
        user_team = list(subordinate)
        try:
            user_emp = Employee.objects.get(user=user) 
            user_team.append(user_emp.pk)           
        except:
            pass
        
        query = Q(employee__user=user) & Q(status__in=cls.get_project_modder(perm)) # if cls.get_project_modder(perm) else Q(employee__user=user)
        proj=Participant.objects.filter(query).values_list("project", flat=True)  
        
        queryset = queryset.filter(Q(employee__in=user_team)|Q(fund__project__in=proj))
        return queryset
    
    
auditlog.register(Expense)
auditlog.register(Contract_expense)
auditlog.register(Contract)
auditlog.register(Expense_point)