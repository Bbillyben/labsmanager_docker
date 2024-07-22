import rules
from .models import Fund
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


def is_user_contribution_manager(user, contrib=None):
    if not contrib:
        return False
    proj_perm = user.has_perm("project.change_project", contrib.fund.project)
    if not contrib.employee:
        return proj_perm
    
    emp_perm = user.has_perm("staff.change_employee", contrib.employee)
    return proj_perm & emp_perm
    
#    Rules ======================

rules.add_perm('fund.change_fund', is_user_fund_project_leader)

rules.add_perm('fund.change_contribution', is_user_contribution_manager)