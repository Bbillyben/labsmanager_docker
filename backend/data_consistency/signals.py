"""Close decisions when the relation they described resolves or changes."""

from django.db import connections
from django.db.models.signals import post_delete, post_migrate, post_save, pre_save
from django.dispatch import receiver
from django.utils import timezone

from expense.models import Contract
from fund.models import Fund
from project.models import Participant

from .models import DataConsistencyException
from .service import CONTRACT_PARTICIPANT_RULE_KEY


_table_exists = {}


@receiver(post_migrate)
def reset_table_cache(**kwargs):
    # Fresh database migrations may save business objects before our initial
    # migration creates the exception table.
    _table_exists.clear()


def close_open(queryset, reason, using):
    if using not in _table_exists:
        _table_exists[using] = DataConsistencyException._meta.db_table in connections[using].introspection.table_names()
    if _table_exists[using]:
        queryset.using(using).filter(rule_key=CONTRACT_PARTICIPANT_RULE_KEY, closed_at__isnull=True).update(
            closed_at=timezone.now(), closed_reason=reason,
        )


@receiver(pre_save, sender=Contract)
def remember_contract_relation(sender, instance, using, **kwargs):
    instance._consistency_old_relation = (
        sender.objects.using(using).filter(pk=instance.pk)
        .values_list("employee_id", "fund_id").first()
        if instance.pk else None
    )


@receiver(post_save, sender=Contract)
def close_changed_contract(sender, instance, using, **kwargs):
    old = getattr(instance, "_consistency_old_relation", None)
    if old is None:
        return
    current = sender.objects.using(using).filter(pk=instance.pk).values_list("employee_id", "fund_id").first()
    if current != old:
        close_open(DataConsistencyException.objects.filter(contract_id=instance.pk), "relation_changed", using)


@receiver(pre_save, sender=Fund)
def remember_fund_project(sender, instance, using, **kwargs):
    instance._consistency_old_project_id = (
        sender.objects.using(using).filter(pk=instance.pk).values_list("project_id", flat=True).first()
        if instance.pk else None
    )


@receiver(post_save, sender=Fund)
def close_changed_fund_project(sender, instance, using, **kwargs):
    old_project_id = getattr(instance, "_consistency_old_project_id", None)
    if old_project_id is None:
        return
    current_project_id = sender.objects.using(using).filter(pk=instance.pk).values_list("project_id", flat=True).first()
    if current_project_id != old_project_id:
        contract_ids = Contract.objects.using(using).filter(fund_id=instance.pk).values("pk")
        close_open(DataConsistencyException.objects.filter(contract_id__in=contract_ids), "relation_changed", using)


@receiver(pre_save, sender=Participant)
def remember_participant_relation(sender, instance, using, **kwargs):
    instance._consistency_old_relation = (
        sender.objects.using(using).filter(pk=instance.pk)
        .values_list("employee_id", "project_id").first()
        if instance.pk else None
    )


@receiver(post_save, sender=Participant)
def close_resolved_participant(sender, instance, using, **kwargs):
    old = getattr(instance, "_consistency_old_relation", None)
    current = sender.objects.using(using).filter(pk=instance.pk).values_list("employee_id", "project_id").first()
    if old and old != current:
        close_open(DataConsistencyException.objects.filter(employee_id=old[0], project_id=old[1]),
                   "relation_changed", using)
    if current:
        close_open(DataConsistencyException.objects.filter(employee_id=current[0], project_id=current[1]),
                   "resolved", using)


@receiver(post_delete, sender=Participant)
def close_deleted_participant(sender, instance, using, **kwargs):
    close_open(DataConsistencyException.objects.filter(employee_id=instance.employee_id,
                                                        project_id=instance.project_id), "relation_changed", using)
