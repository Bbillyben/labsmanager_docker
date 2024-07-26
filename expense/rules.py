import rules
from .models import Contract_expense

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
    

#    Rules ======================

rules.add_perm('expense.change_contract_expense', is_user_contract_project_leader)
# rules.add_perm('expense.change_contract', is_user_contract_project_leader)

rules.add_perm('expense.change_contract', is_user_contract_manager)