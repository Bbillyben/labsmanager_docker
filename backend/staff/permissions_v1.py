"""Contextual Employee mutation capabilities shared with API enforcement."""
from .rules import can_change_employee
from .models import Employee


def can_add_employee(user):
    """Use the Employee creation rule already exposed by the legacy UI."""
    return bool(user.is_authenticated and user.is_active
                and user.has_perm("staff.add_employee")
                and (user.has_perm("staff.change_employee")
                     or Employee.objects.filter(user=user).exists()))


def has_global_employee_visibility(user):
    """Match the unfiltered Employee list/detail queryset permissions."""
    return bool(user.is_staff or user.has_perm("staff.view_employee")
                or user.has_perm("staff.change_employee"))


def generic_info_capabilities(user, employee):
    """Resolve actions after the caller has established Employee visibility."""
    can_change = bool(can_change_employee(user, employee))
    return {
        "can_add": bool(user.has_perm("staff.change_partial_employee", employee)),
        "can_change": can_change,
        "can_delete": can_change,
    }


def leave_capabilities(user, employee):
    can_change = bool(can_change_employee(user, employee))
    return {"can_add": can_change, "can_change": can_change, "can_delete": can_change}


def employee_detail_capabilities(user, employee):
    """Authorize detail editing, including the legacy staff administration role."""
    return {
        "can_change": bool(
            user.is_authenticated and user.is_active
            and (user.is_staff or can_change_employee(user, employee))
        ),
    }
