from django.utils.translation import gettext_lazy as _
from django.contrib.contenttypes.models import ContentType

from settings.models import LMUserSetting
from endpoints.models import Milestones

from datetime import datetime, date, timedelta
from dateutil.relativedelta import relativedelta
from django.db.models import Q, Max, Sum, F

from project.models import Participant
from settings.models import LMUserSetting
from staff.models import Employee, Employee_Superior
from common.models import subscription
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




def _add_notification(user, instance, action, message = None):
    from .models import UserNotification
    repeat = LMUserSetting.get_setting("NOTIFICATION_ENDPOINTS_MILESTONES_REPEAT", user=user, backup_value=0)
    kw={
                'user':user,
                'instance':instance,
                'action':action,
                'repeat_delay':repeat,
                'message': message,
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
        # user's employee
        try:
            emp = Employee.objects.get(user = user.user)
        except:
            continue
        # users employee's subscribed
        content_type = ContentType.objects.get(app_label='staff', model='employee')
        subs_empl = subscription.objects.filter(user = user.user, content_type=content_type).values_list('object_id', flat=True)
        stale=LMUserSetting.get_setting("NOTIFICATION_ENDPOINTS_MILESTONES_STALE", user=user.user, backup_value=0)
        deadline = cdate + relativedelta(days=stale)
        milestonesE = Milestones.objects.filter(end_date__gte=cdate, end_date__lte=deadline, status= False).filter(Q(employee=emp) | Q(employee__id__in=subs_empl))
        
        # for project side
        projects = Participant.objects.filter(Q(employee = emp) & (Q(status = "l") | Q(status="cl") )).values_list("project", flat=True)
        # subscribed project
        content_type = ContentType.objects.get(app_label='project', model='project')
        subs_proj = subscription.objects.filter(user = user.user, content_type=content_type).values_list('object_id', flat=True)
        milestonesP = Milestones.objects.filter(end_date__gte=cdate, end_date__lte=deadline, status= False).filter(Q(project__in = projects) | Q(project__id__in=subs_proj))
        
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
    count = 0
    emp_ct = ContentType.objects.get_for_model(Employee)
    for mil in milestones:
        # check in milestones attribution employees
        
        for emp in mil.employee.filter(~Q(user=None) & Q(is_active=True)): 
            # get user setting for repeat
            notif = _add_notification(emp.user, mil, 'ove')
            if not notif is None:
                    count+=1
        # check for employee's subscription user
        employee_ids = mil.employee.values_list('pk', flat=True)
        for sub_user in subscription.objects.filter(content_type=emp_ct, object_id__in=employee_ids):
            notif = _add_notification(sub_user.user, mil, 'ove')
            if not notif is None:
                    count+=1
        # check in leader and co-leader of the linked project
        for part in Participant.objects.filter(Q(project = mil.project) & ~Q(employee__user=None) & Q(employee__is_active=True) & (Q(status='l'))):
            notif = _add_notification(part.employee.user, mil, 'ove')
            if not notif is None:
                    count+=1
        # check in notification subscribed user
        project_ct = ContentType.objects.get_for_model(mil.project)
        for subs in subscription.objects.filter(content_type=project_ct, object_id=mil.project.id):
            notif = _add_notification(subs.user, mil, 'ove')
            if not notif is None:
                    count+=1
    # print("------------------------------------------------------")
    return count

def check_overload_employee():
    '''
    check if an employee is overloaded and report to its superior
    '''
    print("---------------------------  check_overload_employee")
    count = 0
    employees_over_quotity = (
        Participant.current.filter(Q(employee__is_active=True) & Q(project__status=True))
        .values("employee")
        .annotate(total_quotity=Sum("quotity"))
        .filter(total_quotity__gt=1)
    )
    
    print(f' - overloaded employees : {employees_over_quotity}')
    emp_ct = ContentType.objects.get_for_model(Employee)
    for emp in employees_over_quotity:
        sup = Employee_Superior.objects.filter(Q(employee = emp['employee']) & ~Q(superior__user = None))
        e = Employee.objects.get(pk= emp['employee'])
        # print(f' - sup : {sup}')
        message = _("overloaded up to %s")%emp['total_quotity']
        for s in sup:
            notif = _add_notification(s.superior.user, e, 'ovl', message)
            if not notif is None:
                count+=1
                
        for sub_user in subscription.objects.filter(content_type=emp_ct, object_id=emp['employee']):
            notif = _add_notification(sub_user.user, e, 'ovl', message)
            if not notif is None:
                    count+=1    

    print("------------------------------------------------------")
    
    return count