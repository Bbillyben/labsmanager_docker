import rules
from .models import Project, Participant
from staff.models import Employee, Employee_Superior
from settings.models import LabsManagerSetting

#    Predicates ======================

@rules.predicate
def is_project_leader(user, project = None):
    if not project:
        return False
    try:
        emp = Employee.objects.get(user=user)
        part = Participant.objects.get(project= project, employee = emp)
    except:
        return False
    return part.status=="l"
    
@rules.predicate
def is_project_coleader(user, project = None):
    cet_colead =LabsManagerSetting.get_setting('CO_LEADER_CAN_EDIT_PROJECT')
    if not cet_colead:
        return False
    if not project:
        return False
    
    try:
        emp = Employee.objects.get(user=user)
        part = Participant.objects.get(project= project, employee = emp)
    except:
        return False
    return part.status=="cl"

@rules.predicate
def is_project_participant(user, project = None):
    if not project:
        return False
    part = Participant.objects.filter(project= project, employee__user = user)
    return part.exists()

@rules.predicate
def is_participant_superior(user, participant = None):
    if not participant:
        return False
    try:
        user_emp = Employee.objects.get(user=user)
        return Employee_Superior.is_in_superior_hierarchy(user_emp, participant.employee)
    except:
        return False

from django.contrib.auth.backends import ModelBackend
@rules.predicate
def has_global_change_project(user, project=None):
    return ModelBackend().has_perm(user, "project.change_project")

#    Rules ======================


rules.add_perm('project.change_project', has_global_change_project | is_project_leader |  is_project_coleader)
rules.add_perm('project.view_project', has_global_change_project | is_project_participant)


rules.add_perm('project.view_participant', has_global_change_project | is_participant_superior)

rules.add_perm('project.view_fund',has_global_change_project | is_project_leader |  is_project_coleader)