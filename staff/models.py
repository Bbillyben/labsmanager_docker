from time import altzone
from django.db import models
from django.contrib.auth.models import User
from django.utils.translation import gettext_lazy as _
from django.core.exceptions import ValidationError
from django.db.models import Q, CheckConstraint, F
from django.db.models import Sum

from django.utils import timezone
from datetime import datetime
from auditlog.models import AuditlogHistoryField
from auditlog.registry import auditlog

from faicon.fields import FAIconField

from labsmanager.mixin import ActiveDateMixin

from collections.abc import Iterable

### Models 
class Employee(models.Model):
    
    class Meta:
        """Metaclass defines extra model properties"""
        verbose_name = _("Employee")
        verbose_name_plural = _("Employee")
        ordering = ['first_name']

    """Model for employee"""
    first_name=models.CharField(max_length=40, blank=False, null=False, verbose_name=_('First Name'))
    last_name=models.CharField(max_length=40, blank=False, null=False, verbose_name=_('Last Name'))
    user = models.OneToOneField(User, null=True, blank=True, on_delete=models.CASCADE, verbose_name=_('User'), unique=True)
    birth_date = models.DateField(null=True, blank=True, verbose_name=_('Birth Date'))
    entry_date = models.DateField(null=True, blank=True, verbose_name=_('Entry Date'))
    exit_date = models.DateField(null=True, blank=True, verbose_name=_('Exit Date'))
    email = models.EmailField(null=True, blank=True, verbose_name=_('Email'))
    is_active=models.BooleanField(default=True, null=False, verbose_name=_('Is Active'))
    history = AuditlogHistoryField()
    
    @classmethod
    def get_incomming(cls, timeAdd):
        cdate =datetime.now()
        edate=cdate+ timeAdd
        query = (Q(entry_date__gte=cdate)) & (Q(entry_date__lte=edate))
        return cls.objects.filter(query).order_by('entry_date')
        
    @property
    def user_name(self):
        return self.first_name+" "+self.last_name
    
    def is_team_leader(self):
        return Team.objects.filter(leader=self.pk).exists()

    def is_team_mate(self):
        return TeamMate.objects.filter(employee=self.pk).exists()
    
    def get_status(self):
        return Employee_Status.objects.filter(employee=self.pk)
    
    def get_current_status(self):
        return Employee_Status.current.filter(employee=self.pk)
    # @property
    def contracts(self):
        from expense.models import Contract
        return Contract.objects.filter(employee=self.pk)
    
    #ItemPrice.objects.aggregate(Sum('price'))
    def contracts_quotity(self):
        from expense.models import Contract
        return Contract.effective.current().filter(employee=self).aggregate(Sum('quotity'))["quotity__sum"]

    # @property
    def projects(self):
        from project.models import Participant
        return Participant.objects.filter(employee=self.pk)
    
    def projects_quotity(self):
        from project.models import Participant
        return Participant.current.filter(Q(employee=self.pk) & Q(project__status=True)  ).aggregate(Sum('quotity'))["quotity__sum"]
    
    
    def info(self):
        return GenericInfo.objects.filter(employee=self.pk)
    
    
    def contribution_quotity(self):
        from fund.models import Contribution
        return Contribution.current.filter(employee=self.pk).aggregate(Sum('quotity'))["quotity__sum"]
    
    def has_superior(self):
        return Employee_Superior.current.filter(employee=self.pk).exists()
    
    def get_current_superior(self):
        from staff.models import Employee_Superior
        return Employee_Superior.current.filter(employee=self.pk)
    
    def get_superior(self):
        from staff.models import Employee_Superior
        return Employee_Superior.objects.filter(employee=self.pk)
    
    def has_subordinate(self):
        return Employee_Superior.current.filter(superior=self.pk).exists()
    
    def get_current_subordinate(self):
        from staff.models import Employee_Superior
        return Employee_Superior.current.filter(superior=self.pk, employee__is_active=True)
    
    def get_subordinate(self):
        from staff.models import Employee_Superior
        return Employee_Superior.objects.filter(superior=self.pk)
    
    def __str__(self):
        """Return a string representation of the Employee (for use in the admin interface)"""
        return  f"{self.first_name} {self.last_name}"



class Employee_Status(ActiveDateMixin):
    
    class Meta:
        """Metaclass defines extra model properties"""
        verbose_name = _("Status")
        verbose_name_plural = _("Status")
        
        
    type = models.ForeignKey('Employee_type', on_delete=models.CASCADE, verbose_name=_('Type'))
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, verbose_name=_('Employee'))
    contract_status=(("c",_("Contractual")), 
                ("s", _("Statutory")),
                )
    is_contractual= models.CharField(
        max_length=1,
        choices=contract_status,
        blank=False,
        default='c', verbose_name=_('Is Contractual'),
    )
    history = AuditlogHistoryField()
    
    def __str__(self):
        """Return a string representation of the Status (for use in the admin interface)"""
        return f"{self.employee.first_name} {self.employee.last_name}  : {self.type.name}"
    
class Employee_Superior(ActiveDateMixin):
    class Meta:
        """Metaclass defines extra model properties"""
        verbose_name = _("Superior")
        verbose_name_plural = _("Superiors")
        constraints = [
            CheckConstraint(
                check = ~Q(employee=F('superior')), 
                name = 'check_emp_not_sup',
                violation_error_message=_('Employee and Superior can not be the same person'),
            )]
           
    def __str__(self):
        """Return a string representation of the Status (for use in the admin interface)"""
        return f"Hierarchy relation superior {self.superior} to subordinate {self.employee}"
    
    @classmethod
    def is_in_superior_hierarchy(cls, employee, superior):
        """Check if 'employee' is in the hierarchy of 'superior'"""
        if not isinstance(superior, Iterable):
            superior = [superior]
            
        try:
            relation = Employee_Superior.objects.filter(employee__in=superior)
            if  relation.filter(superior=employee):
                return True
            elif len(relation)==0:
                return False 
            else:
                return Employee_Superior.is_in_superior_hierarchy(employee, relation.values("superior"))
        except Employee_Superior.DoesNotExist:
            return False
        
        
    
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, verbose_name=_('Employee'), related_name="employee")
    superior = models.ForeignKey(Employee, on_delete=models.CASCADE, verbose_name=_('Superior'), related_name="superior_employee")
    history = AuditlogHistoryField()
        
class Employee_Type(models.Model):
    
    class Meta:
        """Metaclass defines extra model properties"""
        verbose_name = _("Employee Type")
        ordering = ['name']
        
    shortname = models.CharField(max_length=30, verbose_name=_('Abbreviation'), unique=True)
    name = models.CharField(max_length=70, verbose_name=_('Name'), unique=True)
    
    def __str__(self):
        """Return a string representation of the Status (for use in the admin interface)"""
        return f"{self.name} ({self.shortname})"

class Team(models.Model):
    class Meta:
        """Metaclass defines extra model properties"""
        verbose_name = _("Team")
    
    name = models.CharField(max_length=70, verbose_name=_('Team Name'), unique=True)
    leader = models.ForeignKey(Employee, on_delete=models.CASCADE, verbose_name=_('Team Leader'))
    history = AuditlogHistoryField()
    
    @property
    def nb_mate(self):
        mates = TeamMate.objects.filter(team=self.pk)
        if mates: return mates.count()
        return 0
    
    @property
    def team_mate(self):
        return TeamMate.objects.filter(team=self.pk)
        
    
    def __str__(self):
        """Return a string representation of the Status (for use in the admin interface)"""
        return f"{self.name}"



class TeamMate(ActiveDateMixin):
    class Meta:
        """Metaclass defines extra model properties"""
        verbose_name = _("TeamMate")    
        
    team = models.ForeignKey(Team, on_delete=models.CASCADE, verbose_name=_('Team'))
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, verbose_name=_('Employee'))

    
    history = AuditlogHistoryField()
    
    
    def __str__(self):
        """Return a string representation of the Status (for use in the admin interface)"""
        return f"{self.team} / {self.employee}"
    
    
    
    def clean(self):
        team = self.team
        inuser = TeamMate.objects.filter(Q(employee=self.employee), Q(team=team), ~Q(pk=self.pk))
        if inuser:
            raise ValidationError(_('Already in Team'))
        isLeader = Team.objects.filter(Q(pk=self.team.pk), Q(leader=self.employee))
        if isLeader:
            raise ValidationError(_('Is Team leader'))
        

class GenericInfoType(models.Model):
    class Meta:
        """Metaclass defines extra model properties"""
        verbose_name = _("Type of Generic Info")
    
    name = models.CharField(max_length=50, unique=True, verbose_name=_('Name'))
    icon = FAIconField(null=True,)
    
    def __str__(self):
        """Return a string representation of the Status (for use in the admin interface)"""
        return self.name

class GenericInfo(models.Model):
    class Meta:
        """Metaclass defines extra model properties"""
        verbose_name = _("Generic Info")
    
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, verbose_name=_('Employee'))
    info =  models.ForeignKey(GenericInfoType, on_delete=models.CASCADE, verbose_name=_('Info Type'))
    value = models.CharField(max_length=150, blank=True, null=True, verbose_name=_('Info Value'))
    history = AuditlogHistoryField()
    
    
    
auditlog.register(Employee)
auditlog.register(Employee_Status)
auditlog.register(Team)
auditlog.register(TeamMate)
auditlog.register(GenericInfo)
auditlog.register(Employee_Superior)