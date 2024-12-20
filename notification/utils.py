from settings.models import LMUserSetting
from endpoints.models import Milestones

from datetime import datetime, date, timedelta
from dateutil.relativedelta import relativedelta
from django.db.models import Q, Max

from project.models import Participant
from settings.models import LMUserSetting
from staff.models import Employee
def check_enabled_notification_user(user, content_type) -> bool:
    '''
    check if a user has enabled/disabled notification for User Notificaiton on app/model 
    settigns name format NOTIFICATION_[APP]_[MODEL]
    '''
    
    app = content_type.app_label.upper()
    model = content_type.model.upper()
    perm = "NOTIFICATION_%s_%s" % (app, model)
    setting = LMUserSetting.get_setting(perm, user=user, backup_value=False)
    # general email setting
    gen_setting=LMUserSetting.get_setting("NOTIFCATION_STATUS", user=user, backup_value=False)
    return setting and gen_setting




def _add_notification(user, instance, action):
    from .models import UserNotification
    repeat = LMUserSetting.get_setting("NOTIFICATION_ENDPOINTS_MILESTONES_REPEAT", user=user, backup_value=0)
    kw={
                'user':user,
                'instance':instance,
                'action':action,
                'repeat_delay':repeat,
            }
    return UserNotification.add_notification(**kw)
###### Check what has to be notified

def check_stale_milestones():
    '''
    check if a milestone enter in stale mode 
    '''
    from .models import UserNotification
    # print("---------------------------  check_stale_milestones")
    cdate = date.today()
    users = LMUserSetting.objects.filter(key = "NOTIFICATION_ENDPOINTS_MILESTONES", value = True)
    count = 0
    for user in users:
        try:
            emp = Employee.objects.get(user = user.user)
        except:
            continue
        
        stale=LMUserSetting.get_setting("NOTIFICATION_ENDPOINTS_MILESTONES_STALE", user=user.user, backup_value=0)
        deadline = cdate + relativedelta(days=stale)
        milestonesE = Milestones.objects.filter(deadline_date__gte=cdate, deadline_date__lte=deadline, status= False, employee = emp)
        projects = Participant.objects.filter(Q(employee = emp) & (Q(status = "l") | Q(status="cl") )).values_list("project", flat=True)
        milestonesP = Milestones.objects.filter(deadline_date__gte=cdate, deadline_date__lte=deadline, status= False, project__in = projects)
        
        milestones = milestonesE.union(milestonesP)
        
        for mil in milestones: 
            notif = _add_notification(user.user, mil, 'sta')
            if not notif is None:
                    count+=1
    # print("------------------------------------------------------")
    return count

def check_overdue_milestones():
    '''
    check if a milestone enter in stale mode 
    '''
    from .models import UserNotification
    
    milestones = Milestones.expired.overdue()
    # print("---------------------------  check_overdue_milestones")
    count = 0
    for mil in milestones:
        # check in milestones attribution employees
        for emp in mil.employee.filter(~Q(user=None) & Q(is_active=True)): 
            # get user setting for repeat
            notif = _add_notification(emp.user, mil, 'ove')
            if not notif is None:
                    count+=1
        # check in leader and co-leader of the linked project
        for part in Participant.objects.filter(Q(project = mil.project) & ~Q(employee__user=None) & Q(employee__is_active=True) & (Q(status='l'))):
            notif = _add_notification(part.employee.user, mil, 'ove')
            if not notif is None:
                    count+=1
    # print("------------------------------------------------------")
    return count