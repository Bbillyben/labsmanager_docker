import rules
from .models import Project, Participant
from staff.models import Employee
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


#    Rules ======================

rules.add_perm('project.change_project', is_project_leader |  is_project_coleader)