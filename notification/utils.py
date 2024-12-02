from settings.models import LMUserSetting
from endpoints.models import Milestones

from datetime import datetime, date, timedelta
from dateutil.relativedelta import relativedelta
from django.db.models import Q, Max



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




###### Check what has to be notified

def check_stale_milestones():
    '''
    check if a milestone enter in stale mode 
    '''
    from .models import UserNotification
    print("---------------------------  check_stale_milestones")
    cdate = date.today()
    milestones = Milestones.objects.filter(deadline_date__gte=cdate)
    count = 0
    for mil in milestones:
        for emp in mil.employee.filter(~Q(user=None)): 
            stale=LMUserSetting.get_setting("NOTIFICATION_ENDPOINTS_MILESTONES_STALE", user=emp.user, backup_value=0)
            repeat = LMUserSetting.get_setting("NOTIFICATION_ENDPOINTS_MILESTONES_REPEAT", user=emp.user, backup_value=0)
            if mil.deadline_date <= cdate+ timedelta(days= stale):
                kw={
                    'user':emp.user,
                    'instance':mil,
                    'action':'sta',
                    'repeat_delay':repeat,
                }
                notif = UserNotification.add_notification(**kw)
                if not notif is None:
                    count+=1
    print("------------------------------------------------------")
    return count

def check_overdue_milestones():
    '''
    check if a milestone enter in stale mode 
    '''
    from .models import UserNotification
    
    milestones = Milestones.expired.overdue()
    print("---------------------------  check_overdue_milestones")
    count = 0
    for mil in milestones:
        for emp in mil.employee.filter(~Q(user=None)): 
            # get user setting for repeat
            repeat = LMUserSetting.get_setting("NOTIFICATION_ENDPOINTS_MILESTONES_REPEAT", user=emp.user, backup_value=0)
            kw={
                'user':emp.user,
                'instance':mil,
                'action':'ove',
                'repeat_delay':repeat,
            }
            notif = UserNotification.add_notification(**kw)
            if not notif is None:
                    count+=1
            
    print("------------------------------------------------------")
    return count