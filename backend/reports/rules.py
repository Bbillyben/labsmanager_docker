from .models import Employee
import rules

from staff.rules import is_user_subordinate

@rules.predicate
def can_print_employee_report(user, employee= None):
    if not employee:
        return False
    if employee.user == user:
        return True
    return is_user_subordinate(user, employee)

@rules.predicate
def can_print_project_report(user, project= None):
    if not project:
        return False
    return user.has_perm("project.change_project", project)


#    Rules ======================
rules.add_perm("reports.view_employeewordreport", can_print_employee_report)
rules.add_perm("reports.view_employeepdfreport", can_print_employee_report)
rules.add_perm("reports.view_projectwordreport", can_print_project_report)
rules.add_perm("reports.view_projectpdfreport", can_print_project_report)

