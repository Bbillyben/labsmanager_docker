from django.db import models
from django.utils.translation import gettext_lazy as _
from django.core.exceptions import ValidationError
from django.db.models import Q, Sum
from staff.models import Employee
from labsmanager.models_utils import PERCENTAGE_VALIDATOR 
from datetime import date
from auditlog.models import AuditlogHistoryField
from auditlog.registry import auditlog
from settings.models import LMUserSetting
from dashboard import utils

from labsmanager.mixin import ActiveDateMixin
from faicon.fields import FAIconField

import logging
logger = logging.getLogger('labsmanager')

class Institution(models.Model):
    class Meta:
        """Metaclass defines extra model properties"""
        verbose_name = _("Lab Institution")
        ordering = ['short_name']
        
    """List of institution public"""
    short_name= models.CharField(max_length=20, unique=True)
    name = models.CharField(max_length=150, unique=True)
    adress=models.CharField(max_length=150, null=True, blank=True)

    def __str__(self):
        """Return a string representation of the Status (for use in the admin interface)"""
        return f"{self.short_name}"
    
class Project(ActiveDateMixin):
    class Meta:
        """Metaclass defines extra model properties"""
        verbose_name = _("project")
        ordering = ['name']
    name = models.CharField(max_length=50, verbose_name=_('Project Name'), unique=True)
    status=models.BooleanField(default=True, verbose_name=_('Project Status'))
    history = AuditlogHistoryField()
    
    def get_status(self):
        return self.status
    get_status.boolean = True
    
    @property
    def get_funds_amount(self):
        from fund.models import Fund
        return Fund.objects.filter(project=self.pk).aggregate(Sum('amount'))["amount__sum"]
    
    @property
    def get_funds_amount_f(self):
        from fund.models import Fund
        return Fund.objects.filter(project=self.pk).aggregate(Sum('amount_f'))["amount_f__sum"]
    
    @property
    def get_funds_expense(self):
        from fund.models import Fund
        return Fund.objects.filter(project=self.pk).aggregate(Sum('expense'))["expense__sum"]
    
    @property
    def get_funds_expense_f(self):
        from fund.models import Fund
        return Fund.objects.filter(project=self.pk).aggregate(Sum('expense_f'))["expense_f__sum"]
    
    @property
    def get_funds_available(self):
        from fund.models import Fund
        fs = Fund.objects.filter(project=self.pk)
        sumA=0
        for f in fs:
            sumA+= f.available
            
        return sumA
    
    @property
    def get_funds_available_f(self):
        from fund.models import Fund
        fs = Fund.objects.filter(project=self.pk)
        sumA=0
        for f in fs:
            sumA+= f.available_f
            
        return sumA
    
    @property
    def get_total_participant_quotity(self):
        parti=Participant.objects.filter(Q(project=self.pk) & (Q(end_date=None) | Q(end_date__gte=date.today()))).only('quotity')
        return parti.aggregate(Sum('quotity'))["quotity__sum"]
    
    @property
    def get_total_contract_quotity(self):
        from expense.models import Contract
        from fund.models import Fund, Fund_Item
        fundP=Fund.objects.filter(project=self.pk).only('pk').all()
        cont=Contract.objects.filter(Q(fund__in = fundP) & (Q(end_date=None) | Q(end_date__gte=date.today()))).only('quotity')
        return cont.aggregate(Sum('quotity'))["quotity__sum"]   
    
    @property
    def info(self):
        return GenericInfoProject.objects.filter(project=self.pk)
    @classmethod
    def staleFilter(cls):
        monthToGo=LMUserSetting.get_setting('DASHBOARD_PROJECT_STALE_TO_MONTH')
        maxDate=utils.getDateToStale(monthToGo)
        return (Q(status=True) & Q(end_date__lte=maxDate))
    
    def __str__(self):
        """Return a string representation of the Status (for use in the admin interface)"""
        return f"{self.name}"
    
    def calculate(self, force=False):
        logger.debug(f'[Project]-calculate :{str(self)} / (force: {force})')
        from fund.models import Fund
        fi= Fund.objects.filter(project=self.pk)
        if fi:
            self.amount= fi.aggregate(Sum('amount'))["amount__sum"]
            self.expense= fi.aggregate(Sum('expense'))["expense__sum"]
        else:
            self.amount = 0
            self.expense = 0
        
def calculate_project(*arg):
        logger.debug('[calculate_project] :'+str(arg))
        pjPk=arg[0]
        if not pjPk or not isinstance(pjPk, int) or pjPk<=0:
            raise KeyError(f'No project id submitted for calculate_project')
        pj=Project.objects.get(pk=pjPk)
        if not pj:
            raise ValueError("No Project Found")
        pj.calculate()
 
 
 
        
class Institution_Participant(models.Model):
    class Meta:
        """Metaclass defines extra model properties"""
        verbose_name = _("Partner Institution")
        unique_together = ('project', 'institution',)
        
    project = models.ForeignKey(Project, on_delete=models.CASCADE, verbose_name=_('Project'))
    institution = models.ForeignKey(Institution, on_delete=models.CASCADE, verbose_name=_('Institution'))
    type_part=(("c",_("Coordinator")), ("p", _("Participant")))
    status = models.CharField(
        max_length=1,
        choices=type_part,
        blank=False,
        default='p', 
        verbose_name=_('Status'),        
    )
    history = AuditlogHistoryField()

class Participant(ActiveDateMixin):

    project = models.ForeignKey(Project, on_delete=models.CASCADE, verbose_name=_('Project'), related_name='participant_project')
    employee =  models.ForeignKey(Employee, on_delete=models.CASCADE, verbose_name=_('Employee'))
    type_part=(("l",_("Leader")), ("cl", _("Co Leader")), ("p", _("Participant")))
    status = models.CharField(
        max_length=2,
        choices=type_part,
        blank=False,
        default='p', 
        verbose_name=_('Status'),        
    )
    quotity = models.DecimalField(max_digits=4, decimal_places=3, default=0, validators=PERCENTAGE_VALIDATOR, verbose_name=_('Time quotity'))
    history = AuditlogHistoryField()
    
    class Meta:
        verbose_name = _("Participant")
        verbose_name_plural = _("Participants")
    
    # def project_name(self):
    #     return self.project.name
    
    # def project_status(self):
    #     return self.project.status
    
    def clean(self):
        project = self.project
        ## user already in team withou end date
        inuser = Participant.objects.filter(Q(employee=self.employee), Q(project=project), ~Q(pk=self.pk), Q(end_date=None))
        if inuser:
            raise ValidationError(_('Already in Team'))
        # user already in but has finished but date between
        q =Q()
        if self.start_date:
            q = (Q(start_date__lte=self.start_date) & Q(end_date__gte=self.start_date))
            if self.end_date:
                q= q | (Q(start_date__lte=self.end_date) & Q(end_date__gte=self.end_date))
        
        inuser = Participant.objects.filter(Q(employee=self.employee), Q(project=project), ~Q(pk=self.pk),
                                            
                                           q
                                            
                                            )
        if inuser:
            raise ValidationError(_('Already in Team At That Date'))


    def __str__(self):
        return self.employee.__str__()

    # def get_absolute_url(self):
    #     return reverse("_detail", kwargs={"pk": self.pk})
    
class GenericInfoTypeProject(models.Model):
    class Meta:
        """Metaclass defines extra model properties"""
        verbose_name = _("Type of Generic Info")
    
    name = models.CharField(max_length=50, unique=True, verbose_name=_('Name'))
    icon = FAIconField(null=True,)
    
    def __str__(self):
        """Return a string representation of the Status (for use in the admin interface)"""
        return self.name

class GenericInfoProject(models.Model):
    class Meta:
        """Metaclass defines extra model properties"""
        verbose_name = _("Generic Info")
    
    project = models.ForeignKey(Project, on_delete=models.CASCADE, verbose_name=_('Project'))
    info =  models.ForeignKey(GenericInfoTypeProject, on_delete=models.CASCADE, verbose_name=_('Info Type'))
    value = models.CharField(max_length=150, blank=True, null=True, verbose_name=_('Info Value'))
    history = AuditlogHistoryField()
    
auditlog.register(Project)
auditlog.register(Institution_Participant)
auditlog.register(Participant)
auditlog.register(GenericInfoProject)