import rules    
from settings.models import LMProjectSetting
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
    print(f"*******************************  [can_user_add_expense_timepoint] ")
    if not fund:
        return False
    setPj = LMProjectSetting.get_setting("EXPENSE_CALCULATION", project=fund.project)
    print(f"    - setting : {setPj}")
    if setPj == "e":
        return False
    
    return user.has_perm("project.change_project", fund.project)
        
#    Rules ======================

rules.add_perm('expense.change_contract_expense', is_user_contract_project_leader)
rules.add_perm('expense.change_expense', is_user_contract_project_leader)
# rules.add_perm('expense.change_contract', is_user_contract_project_leader)

rules.add_perm('expense.change_contract', is_user_contract_manager)

rules.add_perm('expense.add_expense_point', can_user_add_expense_timepoint)

rules.add_perm('expense.change_expense_point', can_user_add_expense_timepoint)