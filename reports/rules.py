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


#    Rules ======================
rules.add_perm("reports.view_employeewordreport", can_print_employee_report)
rules.add_perm("reports.view_employeepdfreport", can_print_employee_report)

