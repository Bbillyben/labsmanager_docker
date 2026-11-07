"""Visibility boundary shared by Equipment and existing financial APIs."""

from django.db.models import Q
from django.db import IntegrityError, transaction
from rest_framework import status
from rest_framework.exceptions import APIException
from rest_framework.exceptions import PermissionDenied

from .models import Equipment, EquipmentExpenseLink


class ExpenseAlreadyAssigned(APIException):
    status_code = status.HTTP_409_CONFLICT
    default_detail = "Expense is already linked to Equipment."


def assignment_capabilities(user, expense):
    """Combine the existing financial edit rule with link permissions."""
    from expense.api_v1 import expense_capabilities
    financial_change = expense_capabilities(user, expense)["can_change"]
    view = user.has_perm("equipment.view_equipmentexpenselink") and user.has_perm("equipment.view_equipment")
    return {
        "can_view": view,
        "can_link": view and financial_change and user.has_perm("equipment.add_equipmentexpenselink"),
        "can_change": view and financial_change and user.has_perm("equipment.change_equipmentexpenselink"),
        "can_unlink": view and financial_change and user.has_perm("equipment.delete_equipmentexpenselink"),
    }


def require_assignment_capability(user, expense, action):
    if not assignment_capabilities(user, expense)[action]:
        raise PermissionDenied()


def create_equipment_link(*, equipment, expense, nature):
    """Enforce one Equipment per Expense, including concurrent association attempts."""
    if EquipmentExpenseLink.objects.filter(expense=expense).exists():
        raise ExpenseAlreadyAssigned()
    try:
        with transaction.atomic():
            return EquipmentExpenseLink.objects.create(equipment=equipment, expense=expense, nature=nature)
    except IntegrityError as error:
        raise ExpenseAlreadyAssigned() from error


def visible_linked_expenses(user, queryset):
    """Keep ordinary Expenses visible; require Equipment rights for linked ones."""
    if not user.has_perm("equipment.view_equipmentexpenselink"):
        return queryset.filter(equipment_link__isnull=True)
    visible = Equipment.get_instances_for_user("view", user, Equipment.objects.all())
    return queryset.filter(
        Q(equipment_link__isnull=True) |
        Q(equipment_link__equipment_id__in=visible.values("pk"))
    )


def require_linked_expense_deletion(user, queryset):
    """Prevent a Fund, Budget, or Contract cascade from bypassing link rights."""
    from expense.api_v1 import expense_capabilities
    linked = queryset.filter(equipment_link__isnull=False).select_related("contract_expense__contract")
    if not linked.exists():
        return
    if (not user.has_perm("equipment.view_equipmentexpenselink") or
            not user.has_perm("equipment.delete_equipmentexpenselink") or
            visible_linked_expenses(user, linked).count() != linked.count()):
        raise PermissionDenied()
    if any(not expense_capabilities(user, item)["can_delete"] for item in linked):
        raise PermissionDenied()
