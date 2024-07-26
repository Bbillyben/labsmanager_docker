from .models import Employee, Employee_Superior, Team, TeamMate
import rules
from settings.models import LabsManagerSetting

#    Predicates ======================
@rules.predicate
def is_user_employee(user, employee = None):
    """ return true if the employee instance is the current linked user employee
    """
    if not employee:
        return False
    return (employee.user == user) & user.has_perm("common.self_edit")

@rules.predicate
def is_user_subordinate(user, employee = None):
    if not employee:
        return False
    try:
        sup = Employee.objects.get(user=user)
    except:
        return False
    setting =LabsManagerSetting.get_setting('EMPLOYEE_CAN_EDIT_SUBORDINATE')
    if setting:
        return Employee_Superior.is_in_superior_hierarchy(sup, employee)
    else:
        return False
    
@rules.predicate
def is_team_leader(user, team= None):
    """ return true if the user's employee instance is the team leader
    """
    if not team:
        return False
    try:
        sup = Employee.objects.get(user=user)
    except:
        return False
    
    return team.leader == sup

@rules.predicate
def is_participant_manager(user, part= None):
    if not part:
        return False
    proj_right = user.has_perm("project.change_project", part.project)
    emp_right = user.has_perm("staff.change_employee", part.employee)
    return proj_right & emp_right


@rules.predicate
def is_teammate(user, team= None):
    if not team:
        return False
    mates = TeamMate.objects.filter(team=team, employee__user=user).exists()
    leader = team.leader.user==user
    return mates | leader

@rules.predicate
def is_teammate_superior(user, teammate= None):
    if not teammate:
        return False
    try:
        user_emp = Employee.objects.get(user=user)
        return Employee_Superior.is_in_superior_hierarchy(user_emp, teammate.employee)
    except:
        return False
    

#    Rules ======================
rules.add_perm('staff.change_employee', is_user_employee |  is_user_subordinate)
rules.add_perm('staff.add_genericinfo', is_user_employee |  is_user_subordinate)
rules.add_perm('staff.change_genericinfo', is_user_employee |  is_user_subordinate)

rules.add_perm('staff.change_team', is_team_leader)
rules.add_perm('staff.view_team', is_teammate)

rules.add_perm('staff.view_teammate', is_teammate_superior)

rules.add_perm('staff.change_participant', is_participant_manager)





