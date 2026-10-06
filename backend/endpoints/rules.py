import rules
from .models import Milestones
from settings.accessor import get_project_setting

@rules.predicate
def is_user_milestone_attribution(user, mile = None):
    ''' Define if a user is in the attribution of a milestones
    '''
    print(f"======================================>>>>>>>>>>>>>>>>>>>>>>>>>>>  Is User Milestone Attrib called")
    if not mile:
        return False
    # if the project parameter allow employee milestones edit

    if not get_project_setting('EMPLOYEE_EDIT_MILESTONE', mile.project):
        return False

    employee = getattr(user, "employee", None)
    if employee and mile.employee.filter(pk=employee.pk).exists():
        return True

@rules.predicate
def is_user_milestone_owner(user, mile = None):
    ''' Define if a user is in the attribution of a milestones
    '''
    if not mile:
        return False
    return user.has_perm('project.change_project', mile.project)


#    Rules ======================
rules.add_perm('endpoints.change_milestones', is_user_milestone_attribution |  is_user_milestone_owner)
