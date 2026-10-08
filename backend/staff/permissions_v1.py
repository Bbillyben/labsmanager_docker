"""Contextual Employee mutation capabilities shared with API enforcement."""
from .rules import can_change_employee


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
