import rules    
from .models import Milestones
from settings.accessor import get_project_setting

@rules.predicate
def is_user_milestone_attribution(user, mile = None):
    ''' Define if a user is in the attribution of a milestones
    '''
    if not mile:
        return False
    # if the project parameter allow employee milestones edit
    print(f">>>>>>>>>>< projec tparam can edit mile : {get_project_setting('EMPLOYEE_EDIT_MILESTONE', mile.project)}")
    if not get_project_setting('EMPLOYEE_EDIT_MILESTONE', mile.project):
        return False
    
    if mile.employee.filter(pk=user.employee.pk).exists():
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