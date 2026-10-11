from django.core.exceptions import ValidationError
from django.conf import settings
from django.db import connection, models, transaction
from django.db.models import F, Q
from django.utils.translation import gettext_lazy as _
from django.utils import timezone

from labsmanager.models_utils import PERCENTAGE_VALIDATOR 
from labsmanager.mixin import SanitizeDataFormMixin, CachedModelMixin
from .manager import milestones_manager
from auditlog.models import AuditlogHistoryField
from auditlog.registry import auditlog

class endpoint(CachedModelMixin, models.Model):
    name = models.CharField(max_length=100, verbose_name=_('endpoint Name'))
    desc =  models.TextField(null=True, blank=True, verbose_name=_('endpoint desc'))
    end_date = models.DateField(null=True, blank=True, verbose_name=_('Deadline Date'))
    
    type_endpoint=[("o",_("one-time")), ("q", _("quantifiable"))]
    type = models.CharField(
        max_length=1,
        choices=type_endpoint,
        blank=False,
        default=type_endpoint[0][0], 
        verbose_name=_('Type'),        
    )
    quotity = models.DecimalField(max_digits=4, decimal_places=3, default=0, validators=PERCENTAGE_VALIDATOR, verbose_name=_('Completion quotity'))
    
    status=models.BooleanField(default=False, verbose_name=_('Endpoints Status'))
    
    cached_vars = ['status', 'quotity']
    class Meta:
        abstract = True
    
    def is_overdue(self):
        # Vérifie si la date limite est dans le passé et si le statut est False
        return self.end_date and self.end_date < timezone.now().date() and not self.status

from labsmanager.mixin import ActiveDateMixin           
class Milestones(endpoint, ActiveDateMixin):
    '''
    Docstring for Milestones
    Milestones represent Both Milestones AND Tasks, a tasks without start date is a Milestone
    '''
    from project.models import Project 
    from staff.models import Employee
    
    objects = models.Manager()
    expired = milestones_manager()
    
    start_date=models.DateField(null=True, blank=True, verbose_name=_('Start Date'),
                                help_text=_('Leave it empty to define as milestone')
                                )
    validated_at = models.DateTimeField(null=True, blank=True, verbose_name=_("Validated at"))
    validated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL,
        related_name="+", verbose_name=_("Validated by"),
    )
    project=models.ForeignKey(Project, on_delete=models.CASCADE, verbose_name=_('Project'))
    history = AuditlogHistoryField()
    employee= models.ManyToManyField(Employee, related_query_name="milestones_by_employee", related_name="milestones", blank=True)
    
    class Meta:
        verbose_name = _("Milestone")
        verbose_name_plural = _("Milestones")
        constraints = [models.CheckConstraint(
            check=(Q(status=True, quotity=1, validated_at__isnull=False)
                   | Q(status=False, quotity__lt=1, validated_at__isnull=True)),
            name="milestones_completion_validation_coherent",
        )]
    @property
    def is_milestone(self):
        return self.start_date is None
    
    def __str__(self):
        """Return a string representation of the Status (for use in the admin interface)"""
        return f"{self.project.name} - {self.name}"

    def normalize_completion(self, validation_user=None):
        """Resolve status/progress transitions for every model save path."""
        previous = type(self).objects.filter(pk=self.pk).values("status", "quotity").first() if self.pk else None
        was_completed = bool(previous and previous["status"])
        status_changed = bool(previous and self.status != previous["status"])
        progress_decreased = bool(previous and self.quotity < 1 and self.quotity != previous["quotity"])

        if was_completed and ((status_changed and not self.status) or progress_decreased):
            # An explicit reopen cannot retain 100% completion.
            self.status = False
            if self.quotity >= 1:
                self.quotity = 0
        elif self.status or self.quotity >= 1:
            self.status = True
            self.quotity = 1
        else:
            self.status = False

        if self.status and not was_completed:
            if self.validated_at is None:
                self.validated_at = timezone.now()
                self.validated_by = None
            if getattr(validation_user, "is_authenticated", False):
                self.validated_by = validation_user
        elif not self.status:
            self.validated_at = None
            self.validated_by = None

    def clean(self):
        super().clean()
        self.normalize_completion()

    def save(self, *args, validation_user=None, **kwargs):
        author = validation_user or getattr(self, "_validation_user", None)
        if hasattr(self, "_validation_user"):
            del self._validation_user
        update_fields = kwargs.get("update_fields")
        if update_fields is not None and not {"status", "quotity"}.intersection(update_fields):
            return super().save(*args, **kwargs)
        self.normalize_completion(author)
        if update_fields is not None:
            kwargs["update_fields"] = set(update_fields) | {"status", "quotity", "validated_at", "validated_by"}
        return super().save(*args, **kwargs)
    

        




auditlog.register(Milestones)


def effective_start_date(item):
    """Use a milestone's deadline as its point-in-time start."""
    return item.start_date or item.end_date


class MilestoneDependency(models.Model):
    """A logical predecessor -> successor relation, without scheduling rules."""

    predecessor = models.ForeignKey(
        Milestones, on_delete=models.CASCADE, related_name="outgoing_dependencies"
    )
    successor = models.ForeignKey(
        Milestones, on_delete=models.CASCADE, related_name="incoming_dependencies"
    )
    history = AuditlogHistoryField()

    class Meta:
        constraints = [
            models.CheckConstraint(
                check=~Q(predecessor=F("successor")),
                name="milestone_dependency_no_self",
            ),
            models.UniqueConstraint(
                fields=("predecessor", "successor"),
                name="milestone_dependency_unique_pair",
            ),
        ]

    @property
    def temporally_inconsistent(self):
        predecessor_start = effective_start_date(self.predecessor)
        successor_start = effective_start_date(self.successor)
        return bool(
            predecessor_start and successor_start and successor_start < predecessor_start
        )

    def clean(self):
        super().clean()
        if not self.predecessor_id or not self.successor_id:
            return
        if self.predecessor_id == self.successor_id:
            raise ValidationError({"predecessor": ValidationError(
                "An item cannot depend on itself.", code="self_dependency"
            )})
        if MilestoneDependency.objects.exclude(pk=self.pk).filter(
            predecessor_id=self.predecessor_id, successor_id=self.successor_id
        ).exists():
            raise ValidationError({"predecessor": ValidationError(
                "This dependency already exists.", code="duplicate"
            )})
        edges = MilestoneDependency.objects.exclude(pk=self.pk).values_list(
            "predecessor_id", "successor_id"
        )
        successors = {}
        for predecessor_id, successor_id in edges:
            successors.setdefault(predecessor_id, []).append(successor_id)
        stack = [self.successor_id]
        seen = set()
        while stack:
            node = stack.pop()
            if node == self.predecessor_id:
                raise ValidationError({"predecessor": ValidationError(
                    "This dependency would create a cycle.", code="cycle"
                )})
            if node not in seen:
                seen.add(node)
                stack.extend(successors.get(node, ()))

    def save(self, *args, **kwargs):
        with transaction.atomic():
            if connection.vendor == "postgresql":
                # Serialize graph writes, including cross-Project cycles.
                with connection.cursor() as cursor:
                    cursor.execute("SELECT pg_advisory_xact_lock(%s)", [291009])
            self.full_clean()
            return super().save(*args, **kwargs)


auditlog.register(MilestoneDependency)
