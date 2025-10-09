import rules
from .models import Fund
from project.rules import is_project_leader, is_project_coleader
from staff.rules import is_employee_superior, is_user_employee

from project.models import Project
from staff.models import Employee

#    Predicates ======================
@rules.predicate
def is_user_fund_project_leader(user, fund = None):
    """ return true if the user as the project change permission
    """
    if not fund:
        return False
    try:
        return user.has_perm('project.change_project', fund.project)
    except:
        return False

@rules.predicate
def is_user_can_see_budget(user, item = None):
    if user.has_perm("fund.view_budget"):
        return True
    if isinstance(item, Project):
        return is_project_leader(user, item) | is_project_coleader(user, item)
    elif isinstance(item, Employee):
        return (item.user == user) | is_employee_superior(user, item)    
    return False

def is_user_contribution_manager(user, contrib=None):
    if not contrib:
        return False
    proj_perm = user.has_perm("project.change_project", contrib.fund.project)
    if not contrib.employee:
        return proj_perm
    
    emp_perm = user.has_perm("staff.change_employee", contrib.employee)
    return proj_perm & emp_perm

#    Rules ======================

rules.add_perm('fund.view_fund', is_project_leader | is_project_coleader)
# rules.add_perm('fund.view_budget', is_project_leader | is_project_coleader)
rules.add_perm('user_view_budget', is_user_can_see_budget)

rules.add_perm('fund.change_fund', is_user_fund_project_leader)
rules.add_perm('fund.change_contribution', is_user_contribution_manager)