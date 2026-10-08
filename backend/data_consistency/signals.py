"""Close decisions when the relation they described resolves or changes."""

from django.db import connections
from django.db.models.signals import post_delete, post_migrate, post_save, pre_save
from django.dispatch import receiver
from django.utils import timezone

from endpoints.models import Milestones
from expense.models import Contract, Expense
from fund.models import Fund
from project.models import Participant, Project
from staff.models import Employee

from .models import DataConsistencyException
from .service import (
    CONTRACT_DATES_RULE_KEY, CONTRACT_EMPLOYEE_DATES_RULE_KEY,
    CONTRACT_FUND_DATES_RULE_KEY, CONTRACT_PARTICIPANT_RULE_KEY,
    EXPENSE_FUND_DATES_RULE_KEY, FUND_DATES_RULE_KEY, MILESTONE_DATES_RULE_KEY,
    PROJECT_LEADER_RULE_KEY, TASK_DATES_RULE_KEY,
)


_table_exists = {}


@receiver(post_migrate)
def reset_table_cache(**kwargs):
    # Fresh database migrations may save business objects before our initial
    # migration creates the exception table.
    _table_exists.clear()


def close_open(queryset, reason, using, rule_key=CONTRACT_PARTICIPANT_RULE_KEY):
    if using not in _table_exists:
        _table_exists[using] = DataConsistencyException._meta.db_table in connections[using].introspection.table_names()
    if _table_exists[using]:
        queryset.using(using).filter(rule_key=rule_key, closed_at__isnull=True).update(
            closed_at=timezone.now(), closed_reason=reason,
        )


@receiver(pre_save, sender=Contract)
def remember_contract_relation(sender, instance, using, **kwargs):
    instance._consistency_old_relation = (
        sender.objects.using(using).filter(pk=instance.pk)
        .values_list("employee_id", "fund_id", "start_date", "end_date").first()
        if instance.pk else None
    )


@receiver(post_save, sender=Contract)
def close_changed_contract(sender, instance, using, **kwargs):
    old = getattr(instance, "_consistency_old_relation", None)
    if old is None:
        return
    current = sender.objects.using(using).filter(pk=instance.pk).values_list("employee_id", "fund_id", "start_date", "end_date").first()
    if current[:2] != old[:2]:
        close_open(DataConsistencyException.objects.filter(contract_id=instance.pk), "relation_changed", using)
    if current != old:
        for key in (CONTRACT_DATES_RULE_KEY, CONTRACT_EMPLOYEE_DATES_RULE_KEY,
                    CONTRACT_FUND_DATES_RULE_KEY):
            close_open(DataConsistencyException.objects.filter(contract_id=instance.pk), "changed", using, key)


@receiver(post_delete, sender=Contract)
def close_deleted_contract(sender, instance, using, **kwargs):
    for key in (CONTRACT_PARTICIPANT_RULE_KEY, CONTRACT_DATES_RULE_KEY,
                CONTRACT_EMPLOYEE_DATES_RULE_KEY, CONTRACT_FUND_DATES_RULE_KEY):
        close_open(DataConsistencyException.objects.filter(contract_id=instance.pk), "deleted", using, key)


@receiver(pre_save, sender=Fund)
def remember_fund_project(sender, instance, using, **kwargs):
    instance._consistency_old_project_dates = (
        sender.objects.using(using).filter(pk=instance.pk)
        .values_list("project_id", "start_date", "end_date").first()
        if instance.pk else None
    )


@receiver(post_save, sender=Fund)
def close_changed_fund_project(sender, instance, using, **kwargs):
    old = getattr(instance, "_consistency_old_project_dates", None)
    if old is None:
        return
    current = sender.objects.using(using).filter(pk=instance.pk).values_list("project_id", "start_date", "end_date").first()
    if current[0] != old[0]:
        contract_ids = Contract.objects.using(using).filter(fund_id=instance.pk).values("pk")
        close_open(DataConsistencyException.objects.filter(contract_id__in=contract_ids), "relation_changed", using)
    if current != old:
        contract_ids = Contract.objects.using(using).filter(fund_id=instance.pk).values("pk")
        expense_ids = Expense.objects.using(using).filter(fund_item_id=instance.pk).values("pk")
        close_open(DataConsistencyException.objects.filter(fund_id=instance.pk), "changed", using,
                   FUND_DATES_RULE_KEY)
        for key in (CONTRACT_DATES_RULE_KEY, CONTRACT_FUND_DATES_RULE_KEY):
            close_open(DataConsistencyException.objects.filter(contract_id__in=contract_ids), "changed", using, key)
        close_open(DataConsistencyException.objects.filter(expense_id__in=expense_ids), "changed", using,
                   EXPENSE_FUND_DATES_RULE_KEY)


@receiver(post_delete, sender=Fund)
def close_deleted_fund(sender, instance, using, **kwargs):
    close_open(DataConsistencyException.objects.filter(fund_id=instance.pk), "deleted", using,
               FUND_DATES_RULE_KEY)


@receiver(pre_save, sender=Project)
def remember_project_dates(sender, instance, using, **kwargs):
    instance._consistency_old_dates = (
        sender.objects.using(using).filter(pk=instance.pk).values_list("start_date", "end_date").first()
        if instance.pk else None
    )


@receiver(post_save, sender=Project)
def close_changed_project_dates(sender, instance, using, **kwargs):
    old = getattr(instance, "_consistency_old_dates", None)
    if old is None:
        return
    current = sender.objects.using(using).filter(pk=instance.pk).values_list("start_date", "end_date").first()
    if current != old:
        for key in (CONTRACT_DATES_RULE_KEY, FUND_DATES_RULE_KEY,
                    MILESTONE_DATES_RULE_KEY, TASK_DATES_RULE_KEY):
            close_open(DataConsistencyException.objects.filter(project_id=instance.pk), "changed", using, key)


@receiver(pre_save, sender=Employee)
def remember_employee_dates(sender, instance, using, **kwargs):
    instance._consistency_old_dates = (
        sender.objects.using(using).filter(pk=instance.pk).values_list("entry_date", "exit_date").first()
        if instance.pk else None
    )


@receiver(post_save, sender=Employee)
def close_changed_employee_dates(sender, instance, using, **kwargs):
    old = getattr(instance, "_consistency_old_dates", None)
    if old is None:
        return
    current = sender.objects.using(using).filter(pk=instance.pk).values_list("entry_date", "exit_date").first()
    if current != old:
        close_open(DataConsistencyException.objects.filter(employee_id=instance.pk), "changed", using,
                   CONTRACT_EMPLOYEE_DATES_RULE_KEY)


@receiver(pre_save, sender=Milestones)
def remember_milestone_relation(sender, instance, using, **kwargs):
    instance._consistency_old_relation = (
        sender.objects.using(using).filter(pk=instance.pk)
        .values_list("project_id", "start_date", "end_date").first()
        if instance.pk else None
    )


@receiver(post_save, sender=Milestones)
def close_changed_milestone(sender, instance, using, **kwargs):
    old = getattr(instance, "_consistency_old_relation", None)
    if old is None:
        return
    current = sender.objects.using(using).filter(pk=instance.pk)
    current = current.values_list("project_id", "start_date", "end_date").first()
    if current != old:
        for key in (MILESTONE_DATES_RULE_KEY, TASK_DATES_RULE_KEY):
            close_open(DataConsistencyException.objects.filter(milestone_id=instance.pk), "changed", using, key)


@receiver(post_delete, sender=Milestones)
def close_deleted_milestone(sender, instance, using, **kwargs):
    for key in (MILESTONE_DATES_RULE_KEY, TASK_DATES_RULE_KEY):
        close_open(DataConsistencyException.objects.filter(milestone_id=instance.pk), "deleted", using, key)


@receiver(pre_save, sender=Expense)
def remember_expense_relation(sender, instance, using, **kwargs):
    instance._consistency_old_relation = (
        sender.objects.using(using).filter(pk=instance.pk).values_list("fund_item_id", "date").first()
        if instance.pk else None
    )


@receiver(post_save, sender=Expense)
def close_changed_expense(sender, instance, using, **kwargs):
    old = getattr(instance, "_consistency_old_relation", None)
    if old is None:
        return
    current = sender.objects.using(using).filter(pk=instance.pk).values_list("fund_item_id", "date").first()
    if current != old:
        close_open(DataConsistencyException.objects.filter(expense_id=instance.pk), "changed", using,
                   EXPENSE_FUND_DATES_RULE_KEY)


@receiver(post_delete, sender=Expense)
def close_deleted_expense(sender, instance, using, **kwargs):
    close_open(DataConsistencyException.objects.filter(expense_id=instance.pk), "deleted", using,
               EXPENSE_FUND_DATES_RULE_KEY)


@receiver(pre_save, sender=Participant)
def remember_participant_relation(sender, instance, using, **kwargs):
    instance._consistency_old_relation = (
        sender.objects.using(using).filter(pk=instance.pk)
        .values_list("employee_id", "project_id", "status").first()
        if instance.pk else None
    )


@receiver(post_save, sender=Participant)
def close_resolved_participant(sender, instance, using, **kwargs):
    old = getattr(instance, "_consistency_old_relation", None)
    current = sender.objects.using(using).filter(pk=instance.pk).values_list("employee_id", "project_id", "status").first()
    if old and old[:2] != current[:2]:
        close_open(DataConsistencyException.objects.filter(employee_id=old[0], project_id=old[1]),
                   "relation_changed", using)
    if current:
        close_open(DataConsistencyException.objects.filter(employee_id=current[0], project_id=current[1]),
                   "resolved", using)
    for relation in (old, current):
        if relation and relation[2] == "l":
            close_open(DataConsistencyException.objects.filter(project_id=relation[1]), "changed", using,
                       PROJECT_LEADER_RULE_KEY)


@receiver(post_delete, sender=Participant)
def close_deleted_participant(sender, instance, using, **kwargs):
    close_open(DataConsistencyException.objects.filter(employee_id=instance.employee_id,
                                                        project_id=instance.project_id), "relation_changed", using)
    if instance.status == "l":
        close_open(DataConsistencyException.objects.filter(project_id=instance.project_id), "changed", using,
                   PROJECT_LEADER_RULE_KEY)
