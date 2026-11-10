"""Equipment catalogue and explicit historical relationships."""

from auditlog.models import AuditlogHistoryField
from auditlog.registry import auditlog
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import F, Q
from django.utils.translation import gettext_lazy as _
from mptt.models import MPTTModel, TreeForeignKey

from labsmanager.mixin import ActiveDateMixin, RightsCheckerMixin


class EquipmentCategory(MPTTModel):
    parent = TreeForeignKey("self", on_delete=models.PROTECT, null=True, blank=True,
                            related_name="children", verbose_name=_("Parent"))
    name = models.CharField(max_length=100, unique=True, verbose_name=_("Name"))
    is_active = models.BooleanField(default=True, verbose_name=_("Active"))

    class Meta:
        ordering = ("tree_id", "lft")
        verbose_name = _("Equipment category")
        verbose_name_plural = _("Equipment categories")

    class MPTTMeta:
        order_insertion_by = ("name",)

    def clean(self):
        super().clean()
        if self.parent_id and self.pk and (
            self.parent_id == self.pk or self.parent.is_descendant_of(self)
        ):
            raise ValidationError({"parent": _("A category cannot be moved under itself or a descendant.")})

    @property
    def path(self):
        """Return category names from the root to this category."""
        return " / ".join(self.get_ancestors(include_self=True).values_list("name", flat=True))

    def __str__(self):
        return self.name


class Equipment(RightsCheckerMixin, models.Model):
    """Stable reference; lifecycle status is independent of maintenance records."""

    class Status(models.TextChoices):
        IN_SERVICE = "in_service", _("In service")
        OUT_OF_SERVICE = "out_of_service", _("Out of service")
        IN_MAINTENANCE = "in_maintenance", _("In maintenance")
        RETIRED = "retired", _("Retired")

    name = models.CharField(max_length=150, verbose_name=_("Name"))
    internal_reference = models.CharField(max_length=100, unique=True, verbose_name=_("Internal reference"))
    category = models.ForeignKey(EquipmentCategory, on_delete=models.PROTECT, related_name="equipment", verbose_name=_("Category"))
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.IN_SERVICE, verbose_name=_("Status"))
    acquisition_date = models.DateField(null=True, blank=True, verbose_name=_("Acquisition date"))
    commissioning_date = models.DateField(null=True, blank=True, verbose_name=_("Commissioning date"))
    decommissioning_date = models.DateField(null=True, blank=True, verbose_name=_("Decommissioning date"))
    history = AuditlogHistoryField()

    class Meta:
        ordering = ("name", "pk")
        indexes = [models.Index(fields=("status", "category"), name="equipment_status_cat_idx")]
        constraints = [
            models.CheckConstraint(
                check=Q(acquisition_date__isnull=True) | Q(commissioning_date__isnull=True) | Q(commissioning_date__gte=F("acquisition_date")),
                name="equipment_acq_comm_order",
            ),
            models.CheckConstraint(
                check=Q(commissioning_date__isnull=True) | Q(decommissioning_date__isnull=True) | Q(decommissioning_date__gte=F("commissioning_date")),
                name="equipment_comm_decomm_order",
            ),
            models.CheckConstraint(
                check=Q(acquisition_date__isnull=True) | Q(decommissioning_date__isnull=True) | Q(decommissioning_date__gte=F("acquisition_date")),
                name="equipment_acq_decomm_order",
            ),
        ]

    def clean(self):
        super().clean()
        if self.category_id and not self.category.is_active:
            previous_category_id = type(self).objects.filter(pk=self.pk).values_list("category_id", flat=True).first() if self.pk else None
            if previous_category_id != self.category_id:
                raise ValidationError({"category": _("Inactive category cannot be selected.")})
        for earlier, later in (("acquisition_date", "commissioning_date"), ("commissioning_date", "decommissioning_date"), ("acquisition_date", "decommissioning_date")):
            left, right = getattr(self, earlier), getattr(self, later)
            if left and right and right < left:
                raise ValidationError({later: _("Date must not precede %(field)s.") % {"field": earlier}})
        if self.pk and type(self).objects.filter(pk=self.pk).exclude(internal_reference=self.internal_reference).exists():
            raise ValidationError({"internal_reference": _("Internal reference cannot be changed.")})

    def __str__(self):
        return f"{self.name} ({self.internal_reference})"


class EquipmentGenericInfoType(models.Model):
    name = models.CharField(max_length=50, unique=True, verbose_name=_("Name"))
    icon = models.CharField(max_length=50, blank=True, null=True)

    class Meta:
        ordering = ("name", "pk")
        verbose_name = _("Type of equipment information")

    def __str__(self):
        return self.name


class EquipmentGenericInfo(models.Model):
    equipment = models.ForeignKey(Equipment, on_delete=models.PROTECT, related_name="generic_info")
    info = models.ForeignKey(EquipmentGenericInfoType, on_delete=models.PROTECT, related_name="values")
    value = models.CharField(max_length=150, blank=True, null=True, verbose_name=_("Info value"))
    history = AuditlogHistoryField()

    class Meta:
        ordering = ("info__name", "pk")
        indexes = [models.Index(fields=("info", "value"), name="equipment_info_value_idx")]
        verbose_name = _("Equipment information")

    def __str__(self):
        return f"{self.info}: {self.value or ''}"


class DatedEquipmentRelation(ActiveDateMixin):
    """Shared inclusive date validation; overlaps remain permitted."""

    class Meta:
        abstract = True

    def clean(self):
        super().clean()
        if self.start_date and self.end_date and self.end_date < self.start_date:
            raise ValidationError({"end_date": _("End date must be on or after start date.")})


class EquipmentResponsibility(DatedEquipmentRelation):
    equipment = models.ForeignKey(Equipment, on_delete=models.PROTECT, related_name="responsibilities")
    employee = models.ForeignKey("staff.Employee", on_delete=models.PROTECT, related_name="equipment_responsibilities")
    history = AuditlogHistoryField()

    class Meta:
        ordering = ("-start_date", "pk")
        indexes = [models.Index(fields=("equipment", "start_date"), name="equipment_resp_start_idx")]
        constraints = [models.CheckConstraint(check=Q(start_date__isnull=True) | Q(end_date__isnull=True) | Q(end_date__gte=F("start_date")), name="equipment_resp_dates")]
        verbose_name = _("Equipment responsibility")

    def __str__(self):
        return f"{self.equipment} — {self.employee}"


class EquipmentInstitutionInventory(DatedEquipmentRelation):
    """Inventory registration, independent of ownership or Equipment status."""

    class Status(models.TextChoices):
        REGISTERED = "registered", _("Registered")
        CLOSED = "closed", _("Closed")

    equipment = models.ForeignKey(Equipment, on_delete=models.PROTECT, related_name="institution_inventories")
    institution = models.ForeignKey("project.Institution", on_delete=models.PROTECT, related_name="equipment_inventories")
    inventory_number = models.CharField(max_length=100, blank=True, verbose_name=_("Inventory number"))
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.REGISTERED)
    history = AuditlogHistoryField()

    class Meta:
        ordering = ("-start_date", "pk")
        indexes = [
            models.Index(fields=("equipment", "institution", "start_date"), name="equipment_inst_dates_idx"),
            models.Index(fields=("institution", "inventory_number"), name="equipment_inv_number_idx"),
        ]
        constraints = [models.CheckConstraint(check=Q(start_date__isnull=True) | Q(end_date__isnull=True) | Q(end_date__gte=F("start_date")), name="equipment_inv_dates")]
        verbose_name = _("Equipment institution inventory")

    @property
    def is_active(self):
        """A closed registration is inactive even when its end date is unknown."""
        return self.status == self.Status.REGISTERED and super().is_active

    def __str__(self):
        return f"{self.equipment} — {self.institution}"


class EquipmentExpenseLink(models.Model):
    """Assign one financial Expense to at most one Equipment."""

    class Nature(models.TextChoices):
        PURCHASE = "purchase", _("Purchase")
        MAINTENANCE = "maintenance", _("Maintenance")
        REPAIR = "repair", _("Repair")
        OTHER = "other", _("Other")

    expense = models.OneToOneField("expense.Expense", on_delete=models.CASCADE, related_name="equipment_link")
    equipment = models.ForeignKey(Equipment, on_delete=models.PROTECT, related_name="expense_links")
    nature = models.CharField(max_length=20, choices=Nature.choices, default=Nature.OTHER)

    class Meta:
        ordering = ("-expense__date", "-pk")
        verbose_name = _("Equipment expense link")

    def __str__(self):
        return f"{self.equipment} — {self.expense}"

    def clean(self):
        super().clean()
        if self.pk and self.maintenances.exclude(equipment_id=self.equipment_id).exists():
            raise ValidationError({"equipment": _("A maintenance uses this link for another Equipment.")})

    def save(self, *args, **kwargs):
        # Every existing write path must preserve the maintenance's parent Equipment.
        self.clean()
        return super().save(*args, **kwargs)


class EquipmentMaintenance(models.Model):
    """One scheduled intervention; calendar events are projections, not rows."""

    class Type(models.TextChoices):
        PREVENTIVE = "preventive", _("Preventive maintenance")
        CORRECTIVE = "corrective", _("Corrective maintenance")
        INSPECTION = "inspection", _("Inspection")
        CALIBRATION = "calibration", _("Calibration")
        OTHER = "other", _("Other")

    class Status(models.TextChoices):
        PLANNED = "planned", _("Planned")
        IN_PROGRESS = "in_progress", _("In progress")
        COMPLETED = "completed", _("Completed")
        CANCELLED = "cancelled", _("Cancelled")

    equipment = models.ForeignKey(Equipment, on_delete=models.PROTECT, related_name="maintenances")
    title = models.CharField(max_length=200)
    maintenance_type = models.CharField(max_length=20, choices=Type.choices)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PLANNED)
    scheduled_date = models.DateField()
    scheduled_start_time = models.TimeField(null=True, blank=True)
    scheduled_end_time = models.TimeField(null=True, blank=True)
    performed_date = models.DateField(null=True, blank=True)
    description = models.TextField(blank=True)
    report = models.TextField(blank=True)
    expense_link = models.ForeignKey(EquipmentExpenseLink, null=True, blank=True,
                                     on_delete=models.SET_NULL, related_name="maintenances")
    history = AuditlogHistoryField()

    class Meta:
        ordering = ("-scheduled_date", "-pk")
        indexes = [models.Index(fields=("scheduled_date", "status"), name="equipment_maint_date_idx")]

    def clean(self):
        super().clean()
        errors = {}
        if self.scheduled_start_time and self.scheduled_end_time and self.scheduled_end_time <= self.scheduled_start_time:
            errors["scheduled_end_time"] = _("End time must be after start time.")
        if bool(self.scheduled_start_time) != bool(self.scheduled_end_time):
            errors["scheduled_end_time"] = _("Provide both times or neither.")
        if self.status == self.Status.COMPLETED and not self.performed_date:
            errors["performed_date"] = _("Completed maintenance requires a performed date.")
        if self.expense_link_id and self.equipment_id and self.expense_link.equipment_id != self.equipment_id:
            errors["expense_link"] = _("The expense link belongs to another Equipment.")
        if errors:
            raise ValidationError(errors)

    def __str__(self):
        return self.title

    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)


for model in (Equipment, EquipmentGenericInfo, EquipmentResponsibility, EquipmentInstitutionInventory, EquipmentMaintenance):
    auditlog.register(model)
