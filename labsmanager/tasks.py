
from django.core.mail import EmailMessage
from django.db.models import Q, Sum
from django.template.loader import render_to_string
from django.http import HttpResponse

from .utils import send_email

from django.contrib.auth import get_user_model 
from django_q.tasks import async_task

from settings.models import LabsManagerSetting
import datetime
from django.utils import timezone


from auditlog.models import LogEntry


import logging
logger = logging.getLogger('labsmanager')



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