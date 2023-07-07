
import datetime
from django.contrib.sites.models import Site
from labsmanager import settings
from django.core.mail import send_mail, EmailMultiAlternatives
from email.mime.image import MIMEImage
from functools import lru_cache
from settings.models import LabsManagerSetting
from django.template.loader import render_to_string
from django.utils.html import strip_tags

from django.contrib.staticfiles import finders
from django.core.exceptions import ObjectDoesNotExist

import logging
logger = logging.getLogger('labsmanager')

class BaseMail():
    """ Use to send basic email, with template generation.
    Send class method can be directly called if necessary
     """
    mail_template="email/base_email.html"
    logo_path="img/labsmanager/labsmanager_icon.png"
    subject = "Labs Manager Mail"
    from_email=None
    
    def generate_context(self, **kwargs):
        self.context={}
        self.context["base_url"]=Site.objects.get_current()
        self.context["current_date"]=datetime.datetime.now()
        
        return self.context
    
    def send(self, recipients, addLogo=False, **kwargs):
        
        if recipients == None :
            logger.error(f"Notification Send  has no user email defined : {user}")
            return None
        
        
        self.generate_context(**kwargs)
        html_message=  render_to_string(self.__class__.mail_template,self.context)
        body = strip_tags(html_message)
        
        if 'subject' in kwargs:
            self.subject = kwargs["subject"]
        else:
            self.subject = self.__class__.subject
        
        if 'from_email' in kwargs:
            self.from_email = kwargs["from_email"]
        else:
            self.from_email = self.__class__.from_email
            
        
        if addLogo == True:
            return self.__class__.send_logo_mail(self.subject, body, recipients, self.from_email, html_message)
        else:
            return self.__class__.send_email(self.subject, body, recipients, self.from_email, html_message)
        
    
    @classmethod
    def logo_data(cls):
        with open(finders.find(cls.logo_path), 'rb') as f:
            logo_data = f.read()
        logo = MIMEImage(logo_data)
        logo.add_header('Content-ID', '<logo>')
        return logo
    
    @classmethod
    def send_logo_mail(cls, subject, body, recipients, from_email=None, html_message=None):
        if type(recipients) == str:
            recipients = [recipients]
            
        if from_email == None:
            from_email=settings.EMAIL_SENDER
        
         # get the subject prefix from settings
        subject_prefix=LabsManagerSetting.get_setting("MAIL_OBJECT_PREFIX")
        if subject_prefix:
            subject= subject_prefix+" "+subject
            
        message = EmailMultiAlternatives(
            subject=subject,
            body=body,
            from_email=from_email,
            to=recipients,
        )
        message.mixed_subtype = 'related'
        message.attach_alternative(html_message, "text/html")
        message.attach(cls.logo_data())
        response= message.send(fail_silently=False)
        return response
    
    @classmethod
    def send_email(cls, subject, body, recipients, from_email=None, html_message=None):
        from settings.models import LabsManagerSetting
        
        if type(recipients) == str:
            recipients = [recipients]
        
        if from_email == None:
            from_email=settings.EMAIL_SENDER
            
        # get the subject prefix from settings
        subject_prefix=LabsManagerSetting.get_setting("MAIL_OBJECT_PREFIX")
        if subject_prefix:
            subject= subject_prefix+" "+subject
            
        response = send_mail(
            subject,
            body,
            from_email,
            recipients,
            html_message=html_message,
            fail_silently=False,
        )
        return response
    
    
from settings.models import LMUserSetting
from labsmanager.utils import get_choiceitem
from django_q.models import Schedule
from common.models import subscription
from project.models import Project
from fund.models import Fund
from staff.models import Employee, Team, TeamMate
from expense.models import Contract
from leave.models import Leave
from django.contrib.contenttypes.models import ContentType
from dashboard import utils
from project.views import get_project_fund_overviewReport_bytType
from django.db.models import Q

class SubscriptionMail(BaseMail):
    """ Class to generate and send Notification email from subscription
    has to be a user parameter in kwargs
     """
    mail_template="email/notification_email.html"
    subject = "Notification Report"

    def generate_context(self, **kwargs):
        
        super().generate_context(**kwargs)
        
        if not 'user' in kwargs:
            raise ObjectDoesNotExist("User Not defined for [SubscriptionMail]")
        user = kwargs['user']
        
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
            
        self.context.update({
            'user':user,
            'sub_status':sub_enab,
            'report_leave':leaves_report,
            'sub_freq':freq_name, 
            'next_date':next_date,    
        })
        # get subscription
        subs = subscription.objects.filter(user=user.pk)
        # get subscription
        subs = subscription.objects.filter(user=user.pk)
        
        
        
        # for projects
        conttype_proj = ContentType.objects.get(app_label="project", model="project")
        proj_ids = subs.filter(content_type= conttype_proj).values_list("object_id")
        projects = Project.objects.filter(pk__in = proj_ids).order_by("name")
        fund_lines = Fund.objects.filter(project__in=proj_ids).order_by("project__name")
        
        self.context['projects']=projects
        self.context['funds']=fund_lines
        
        for pj in projects:
            fo = get_project_fund_overviewReport_bytType(pj.pk)
            self.context['fund_o_'+str(pj.name)] = fo
        
        
        # for employees
        conttype_emp = ContentType.objects.get(app_label="staff", model="employee")
        emp_ids = subs.filter(content_type= conttype_emp).values_list("object_id")
        employees  = Employee.objects.filter(pk__in = emp_ids).order_by("last_name")
        
        # for active contract
        contracts = Contract.objects.filter(employee__in=emp_ids, is_active=True)
        
        self.context['employees']=employees 
        self.context['contracts']= contracts
        
        # for team
        
        conttype_team = ContentType.objects.get(app_label="staff", model="team")
        team_ids  = subs.filter(content_type= conttype_team).values_list("object_id")
        teams = Team.objects.filter(pk__in = team_ids).order_by("name")
        self.context['teams']=teams 
        
        slot = utils.getCurrentMonthTimeslot()
        
        for t in teams:
            tm = TeamMate.current.filter(team=t).values('employee')
            tmE = Employee.objects.filter(Q(pk__in=tm) | Q(pk=t.leader.pk))
            self.context['teammate_'+str(t.name)]=tmE 
            leave=Leave.objects.timeframe(slot).filter(employee__in=tmE).order_by('-end_date')    
            self.context['leave_'+str(t.name)]=leave 
        
        if leaves_report:
            lv=Leave.objects.timeframe(slot).all().order_by('-end_date')  
            self.context['all_leaves']=lv 
            self.context['current_month']=slot['from'].strftime('%B')