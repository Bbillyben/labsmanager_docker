from .models import Employee
import rules

from staff.rules import is_user_subordinate

@rules.predicate
def can_print_employee_report(user, employee= None):
    """Check whether a user may export a report for an Employee."""
    if not employee:
        return False
    if employee.user == user:
        return True
    return is_user_subordinate(user, employee)

@rules.predicate
def can_print_project_report(user, project= None):
    """Check whether a user may export a report for a Project."""
    if not project:
        return False
    return user.has_perm("project.change_project", project)


@rules.predicate
def can_print_equipment_report(user, equipment=None):
    """Permit object-level exports to users who may edit this Equipment."""
    return bool(equipment and user.has_perm("equipment.change_equipment", equipment))


#    Rules ======================
rules.add_perm("reports.view_employeewordreport", can_print_employee_report)
rules.add_perm("reports.view_employeepdfreport", can_print_employee_report)
rules.add_perm("reports.view_projectwordreport", can_print_project_report)
rules.add_perm("reports.view_projectpdfreport", can_print_project_report)
rules.add_perm("reports.view_equipmentwordreport", can_print_equipment_report)
rules.add_perm("reports.view_equipmentpdfreport", can_print_equipment_report)

