from .models import subscription
from django.contrib.auth.models import User
from django.utils.translation import gettext_lazy as _
from django.contrib.contenttypes.models import ContentType
from django.db.models import Q

from django.template.loader import render_to_string
from django.utils.html import strip_tags

from django_q.models import Schedule

from django.shortcuts import render, HttpResponse
from settings.models import LMUserSetting
from django.contrib.sites.models import Site

from project.models import Project
from fund.models import Fund
from staff.models import Employee, Team, TeamMate
from expense.models import Contract
from leave.models import Leave

from dashboard import utils


from labsmanager.utils import send_email, get_choiceitem
from project.views import get_project_fund_overviewReport_bytType
import logging
logger = logging.getLogger('labsmanager')



def checkuser_notification_tasks(user):
    currSch = Schedule.objects.filter(name='send_notification_'+str(user.username))
    sub_enab =  LMUserSetting.get_setting("NOTIFCATION_STATUS", user=user)
    
    # print("  - user : "+str(user)+" / "+str(user.pk))
    # print("  - NOTIFCATION_STATUS : "+str(sub_enab))
    # print("  - schedule : "+str(currSch))
    
    if not currSch and sub_enab:
        logger.debug(f"Notification task for User {user.username} do not exist")
        sch = Schedule.objects.create(name='send_notification_'+str(user.username),
                                    func='common.tasks.send_notification',
                        schedule_type=Schedule.CRON,
                        cron = '5 4 * * *',
                        kwargs={'user_pk':user.pk, 'username':user.username},
                        #hook="labsmanager.tasks.sendSuperUserMail",
                        )
        logger.debug("New Schedule :"+str(sch))
    
    if currSch and not sub_enab:
        logger.debug(f"delete Notification task for User {user.username}")
        currSch.delete()
        return
    
        
    currSch = Schedule.objects.get(name='send_notification_'+str(user.username))
    if not currSch :
        return
    
    freq = LMUserSetting.get_setting("NOTIFCATION_FREQ",  user=user)
    # print("  - NOTIFCATION_FREQ : "+str(freq))
    
    if currSch.cron != freq:
        currSch.cron = freq
        currSch.save()
        logger.debug(f"Update Notification cron for user {user.username} at {freq}")
    
def check_notifications_tasks():
    logger.debug(f"[check_notifications_tasks] called")
    # get all user involved
    users=subscription.objects.all().values("user")
    users=users.distinct("user")
    
    for u_pk in users:
        user = User.objects.get(pk=u_pk['user'])
        if not user:
            logger.error(f"Notification User {u_pk['user']} do not exist in DB")
            continue
        checkuser_notification_tasks(user)        

def generate_notif_mail_context(user):
    
    logger.debug(f" Send notification for user : {user.username}")
    context = {}
    # subscription parameters
    
    sub_enab =  LMUserSetting.get_setting("NOTIFCATION_STATUS", user=user)
    freq = LMUserSetting.get_setting("NOTIFCATION_FREQ",   user=user)
    choices=LMUserSetting.get_setting_choices("NOTIFCATION_FREQ")
    leaves_report=LMUserSetting.get_setting("NOTIFCATION_INC_LEAVE", user=user)
    freq_name=get_choiceitem(choices, freq)
    
    if sub_enab == True:
        currSch = Schedule.objects.get(name='send_notification_'+str(user.username))
        next_date = currSch.next_run
    else:
        next_date = "-"
    
    current_site = Site.objects.get_current()

    context.update({
        'user':user,
        'sub_status':sub_enab,
        'report_leave':leaves_report,
        'sub_freq':freq_name, 
        'next_date':next_date,  
        'site':current_site.domain,   
    })
    
    

    # get subscription
    subs = subscription.objects.filter(user=user.pk)
    
    
    
    # for projects
    conttype_proj = ContentType.objects.get(app_label="project", model="project")
    proj_ids = subs.filter(content_type= conttype_proj).values_list("object_id")
    projects = Project.objects.filter(pk__in = proj_ids).order_by("name")
    fund_lines = Fund.objects.filter(project__in=proj_ids).order_by("project__name")
    
    context['projects']=projects
    context['funds']=fund_lines
    
    for pj in projects:
        fo = get_project_fund_overviewReport_bytType(pj.pk)
        context['fund_o_'+str(pj.name)] = fo
    
    
    # for employees
    conttype_emp = ContentType.objects.get(app_label="staff", model="employee")
    emp_ids = subs.filter(content_type= conttype_emp).values_list("object_id")
    employees  = Employee.objects.filter(pk__in = emp_ids).order_by("last_name")
    
    # for active contract
    contracts = Contract.objects.filter(employee__in=emp_ids, is_active=True)
    
    context['employees']=employees 
    context['contracts']= contracts
    
    # for team
    
    conttype_team = ContentType.objects.get(app_label="staff", model="team")
    team_ids  = subs.filter(content_type= conttype_team).values_list("object_id")
    teams = Team.objects.filter(pk__in = team_ids).order_by("name")
    context['teams']=teams 
    
    slot = utils.getCurrentMonthTimeslot()
    
    for t in teams:
        tm = TeamMate.current.filter(team=t).values('employee')
        tmE = Employee.objects.filter(Q(pk__in=tm) | Q(pk=t.leader.pk))
        context['teammate_'+str(t.name)]=tmE 
        leave=Leave.objects.timeframe(slot).filter(employee__in=tmE).order_by('-end_date')    
        context['leave_'+str(t.name)]=leave 
    
    if leaves_report:
        lv=Leave.objects.timeframe(slot).all().order_by('-end_date')  
        context['all_leaves']=lv 
    
    
    return context 

def send_notification(*args, **kwargs):
    print("###############   [cdmmon.tasks.send_notification]    #######")
    pkU = kwargs.get("user_pk", None)
    if pkU == None:
        logger.error(f"Notification Send  has no user defined in kwargs : {kwargs}")
        return None    
    user = User.objects.get(pk=pkU)
    ## SEND MAIL
    
    html_message=  render_to_string('email/notification_email.html', generate_notif_mail_context(user))
    body = strip_tags(html_message)
    
    recipient = user.email
    if recipient == None :
        logger.error(f"Notification Send  has no user email defined : {user}")
        return None

    response = send_email(
        subject=_("Subscription Report"),
        body=body,
        recipients=recipient,
        from_email=None,
        html_message=html_message
    )
    logger.debug(f" Mail sending  to {recipient}")
    return response
    
from django.core.exceptions import ObjectDoesNotExist
def send_test_mail(request, *args, **kwargs):
    logger.info("[send_test_mail] Called")
    
    upk = request.POST.get("user", None)
    
    user = User.objects.filter(pk=upk)
    if user == None:
         raise ObjectDoesNotExist(f"Test Mail Sending : User not found : ({upk})") 
    user= user.first() 
    logger.debug(f" Send test mail  to user {user} ({upk})")
    
    response = send_notification(user_pk=user.pk)
    if response == None:
        raise ObjectDoesNotExist(f"Test Mail Sending Error, reponse : {response}") 
        
    return HttpResponse("success")   

def test_check(request):    

    upk = request.GET["user"]
    
    send_test = request.GET.get("mail", None)
    if send_test != None:
        send_notification(user_pk = upk)
    
    user = User.objects.get(pk=upk)
    return render(request=request,template_name="email/notification_email.html",context=generate_notif_mail_context(user))