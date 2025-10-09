import rules    
from settings.models import LMProjectSetting
from fund.rules import is_user_fund_project_leader
from project.rules import is_project_leader, is_project_coleader
from staff.rules import is_employee_superior, is_user_employee

from project.models import Project
from staff.models import Employee
#    Predicates ======================
@rules.predicate
def is_user_contract_project_leader(user, cont = None):
    """ return true if the user as the project change permission
    """
    if not cont:
        return False
    try:
        return user.has_perm('project.change_project', cont.fund.project)
    except:
        return False

@rules.predicate
def is_user_contract_manager(user, contract=None):
    """ return true if the user as project right AND employee rigth
    
    """
    if not contract:
        return False
    proj_right = user.has_perm("project.change_project", contract.fund.project)
    emp_right = user.has_perm("staff.change_employee", contract.employee)
    return proj_right & emp_right
    
@rules.predicate
def can_user_add_expense_timepoint(user, fund=None):
    if not fund:
        return False
    setPj = LMProjectSetting.get_setting("EXPENSE_CALCULATION", project=fund.project)
    if setPj == "e":
        return False
    
    return user.has_perm("project.change_project", fund.project)

@rules.predicate
def can_user_view_contract(user, item):
    """ test if a user has right to see contract (general), contract_list (common rights) or either 
    is project leader or coleader
    is employee or employee's superior
    """
    if user.has_perm("common.contract_list") or user.has_perm("expense.view_contract"):
        return True
    if isinstance(item, Project):
        return is_project_leader(user, item) | is_project_coleader(user, item)
    elif isinstance(item, Employee):
        return (item.user == user) | is_employee_superior(user, item)    
    
    return False
        
#    Rules ======================

rules.add_perm('expense.change_contract_expense', is_user_contract_project_leader)
rules.add_perm('expense.change_expense', is_user_contract_project_leader)
rules.add_perm('expense.add_expense', is_user_fund_project_leader)
# rules.add_perm('expense.change_contract', is_user_contract_project_leader)

rules.add_perm('expense.change_contract', is_user_contract_manager)

rules.add_perm('expense.add_expense_point', can_user_add_expense_timepoint)

rules.add_perm('expense.change_expense_point', can_user_add_expense_timepoint)


rules.add_perm('common.contract_list', is_project_leader | is_project_coleader)
rules.add_perm('user_view_contract', can_user_view_contract)