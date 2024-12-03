
from django.core.mail import EmailMessage
from django.db.models import Q, Sum
from django.template.loader import render_to_string
from django.http import HttpResponse

from .utils import send_email

from django.contrib.auth import get_user_model 
from django_q.tasks import async_task
from django_q.models import Schedule


from settings.models import LabsManagerSetting
from fund.models import Fund
import datetime
from django.utils import timezone


from auditlog.models import LogEntry


import logging
logger = logging.getLogger('labsmanager')


# =========== Task global scheduler on start up call ========== #
def scheduleBaseTasks():
    logger.debug("[scheduleBaseTasks] starting ...")
    # for audit log cleaning
    currSch = Schedule.objects.filter(func='labsmanager.tasks.clean_auditlog')
    if not currSch:
        sch = Schedule.objects.create(name="clean_auditlog",
                                      func='labsmanager.tasks.clean_auditlog',
                            #hook='hooks.print_result',
                            schedule_type=Schedule.CRON,
                            cron = '0 3 1 * *',
                            #hook="labsmanager.tasks.sendSuperUserMail",
                            )
        logger.debug("New Schedule :"+str(sch))
    else:
        logger.debug("Already in schedules :"+str(currSch))
    
    # for Fund update calculation
    currSch = Schedule.objects.filter(func='labsmanager.tasks.update_all_calculation')
    if not currSch:
        sch = Schedule.objects.create(name="update_all_calculation",
                                      func='labsmanager.tasks.update_all_calculation',
                            #hook='hooks.print_result',
                            schedule_type=Schedule.CRON,
                            cron = '30 3 * * 1-5',
                            #hook="labsmanager.tasks.sendSuperUserMail",
                            )
        logger.debug("New Schedule :"+str(sch))
    else:
        logger.debug("Already in schedules :"+str(currSch))
        
        
    # for Notifications
    # check stale and overdue
    currSch = Schedule.objects.filter(func='notification.tasks.check_all_notification')
    if not currSch:
        sch = Schedule.objects.create(name="check_user_notifications_tasks",
                                      func='notification.tasks.check_all_notification',
                                    schedule_type=Schedule.CRON,
                                    cron = '50 1 * * 1-5',
                                )
        logger.debug("New Schedule :"+str(sch))
    else:
        logger.debug("Already in schedules :"+str(currSch))
    # send pending notification
    currSch = Schedule.objects.filter(func='notification.tasks.send_pending_notification')
    if not currSch:
        sch = Schedule.objects.create(name="send_user_notifications_tasks",
                                      func='notification.tasks.send_pending_notification',
                                        schedule_type=Schedule.CRON,
                                        cron = '00 2 * * 1-5',
                                    )   
        logger.debug("New Schedule :"+str(sch))
    else:
        logger.debug("Already in schedules :"+str(currSch))
   
    # for Subscription
    
    currSch = Schedule.objects.filter(func='common.tasks.check_notifications_tasks')
    if not currSch:
        sch = Schedule.objects.create(name="check_notifications_tasks",
                                      func='common.tasks.check_notifications_tasks',
                            #hook='hooks.print_result',
                            schedule_type=Schedule.HOURLY,
                            #hook="labsmanager.tasks.sendSuperUserMail",
                            )
        logger.debug("New Schedule :"+str(sch))
    else:
        logger.debug("Already in schedules :"+str(currSch))
    
    # check periodically the scheduled tasks
    currSch = Schedule.objects.filter(func='labsmanager.tasks.scheduleBaseTasks')
    if not currSch:
        sch = Schedule.objects.create(name="scheduleBaseTasks",
                                      func='labsmanager.tasks.scheduleBaseTasks',
                            #hook='hooks.print_result',
                            schedule_type=Schedule.CRON,
                            cron = '30 1 * * 1-5',
                            #hook="labsmanager.tasks.sendSuperUserMail",
                            )
        logger.debug("New Schedule :"+str(sch))
    else:
        logger.debug("Already in schedules :"+str(currSch))
    


# --------------- Clean the audi log based on retention Setting
def clean_auditlog():
    logger.debug("[clean_auditlog] starting ...")
    # get settings for audit log retention
    ret_time=LabsManagerSetting.get_setting("AUDIT_LOG_RETENTION")
    if not ret_time:
        logger.warn("[clean_auditlog] - NO RETENTION TIME DEFINED")
        return
    logger.debug("    - retention time :"+str(ret_time))
    
    tod = datetime.datetime.now()
    d = datetime.timedelta(days = ret_time)
    a = tod - d
    logger.debug("    -> All history logs will be cleaned before :"+str(a))
    entries = LogEntry.objects.all()
    entries = entries.filter(timestamp__date__lt=a)
    cc=entries.delete()
    logger.debug("    >>> "+str(cc[0])+" entries has been deleted ")
    pass


# --------------- Update all Expense and Fund calculation
def update_all_calculation():
    logger.debug("[update_all_calculation] starting ...")
    fu=Fund.objects.all()
    for f in fu:
        f.calculate(force=True)
# --------------- Generate a report to send
def create_report(*args, **kwargs):
    from staff.models import Employee
    from project.models import Participant
    
    contextMail={}
    parti=Participant.objects.select_related("employee").filter(Q(project__status=True) &  Q(start_date__lte=timezone.now())  & ( Q(end_date__gte=timezone.now()) | Q(end_date=None))).values("employee").annotate(project_quotity=Sum('quotity'))
    parti=parti.filter(project_quotity__gt=1).values("employee")
    emp=Employee.objects.filter(pk__in=parti)
    contextMail['participant']=emp
    
    
    
    html_content = render_to_string('email/global_report.html',context=contextMail)
    return HttpResponse(html_content, status=200)

def sendMailTest(*args, **kwargs):    
    logger.debug("[send_email_test] starting ...")
    
    logger.debug("  - args :"+str(args))
    logger.debug("  - kwargs :"+str(kwargs))
    
    User = get_user_model()
    usersObj = User.objects.all()
    emailadress=kwargs["recipient"]
    
    
    contextEmail={"users":usersObj,}
    html_content = render_to_string('email/user_list.html',context=contextEmail)
    
    logger.debug("  - emailadress :"+str(emailadress))
    logger.debug("  - contextEmail :"+str(contextEmail))
    logger.debug("  - html_content :"+str(html_content))
    resp=send_email(
        subject="Test Email", 
        body="",
        recipients=emailadress,
        from_email=None,
        html_message=html_content
        )
    logger.debug(">>>>> mail response :"+str(resp))
    
    
    
# ============================================ send mail hook to super user
def sendSuperUserMail(*args, **kwargs):
    logger.debug("[sendSuperUserMail] starting ...")
    User = get_user_model()
    usersMails = User.objects.filter(is_superuser=True).values_list("email", flat=True)
    
    task=args[0]
    
    content=f"The task : {task.name} has finished \n"
    content+=f" - fct : {task.func} \n"
    
    
    resp=send_email(
        subject="Task Hook Mail", 
        body="Test HookMail Body",
        recipients=usersMails,
        from_email=None,
        html_message=content
        )
    logger.debug(">>>>> mail response :"+str(resp))
    
# test hook
def testHook(*args, **kwargs):
    pass
    