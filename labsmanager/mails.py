
import datetime
from django.contrib.sites.models import Site
from labsmanager import settings
from django.core.mail import send_mail, EmailMultiAlternatives
from email.mime.image import MIMEImage
from functools import lru_cache
from settings.models import LabsManagerSetting
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from django.utils import translation

from django.contrib.staticfiles import finders
from django.core.exceptions import ObjectDoesNotExist
from dateutil.relativedelta import relativedelta
from labsmanager.utils import randomID
from labsmanager import serializers
import re
import logging
logger = logging.getLogger('labsmanager')


class BaseMail():
    """ Use to send basic email, with template generation.
    define template path with mail_template
        Send class method can be directly called if necessary
     """
    mail_template="email/base_email.html"
    default_subject = "Labs Manager Mail"
    from_email=None
    
    
    
    def generate_context(self, **kwargs):
        self.context={}
        self.context["base_url"]=Site.objects.get_current()
        self.context["current_date"]=datetime.datetime.now()
        
        return self.context
    
    def render_html(self, **kwargs):
        html = render_to_string(self.__class__.mail_template,self.context)
        return html
    
    def render_body(self, html, **kwargs):
        body = re.sub(r'<style>.*?</style>', '', html, flags=re.DOTALL)
        body = strip_tags(body)
        return body
    
    def send(self, recipients, **kwargs):
        
        if recipients == None :
            logger.error(f"Notification Send  has no user email defined : {recipients}")
            return None
        
        
        self.generate_context(**kwargs)
        html_message=  self.render_html(**kwargs) # render_to_string(self.__class__.mail_template,self.context)
        body = self.render_body(html_message)
        
        if 'subject' in kwargs:
            self.subject = kwargs["subject"]
        else:
            self.subject = self.__class__.default_subject
        
        if 'from_email' in kwargs:
            self.from_email = kwargs["from_email"]
        else:
            self.from_email = self.__class__.from_email
            
        return self.__class__.send_email(self.subject, body, recipients, self.from_email, html_message, **kwargs)
        
    
    @classmethod
    def send_email(cls, subject, body, recipients, from_email=None, html_message=None, **kwargs):
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



class EmbedImgMail(BaseMail):
    """ Extends Base Mail
    Able to embed images from static dir (see labsmanager.settings.STATIC_URL)
    To embed img add in kwargs of send method :  'embedImg':True
    source of image should start with /STATIC_ULR/ (as included with {% static 'path/to/img.png' %})
    """
    
    @classmethod
    def send_email(cls, subject, body, recipients, from_email=None, html_message=None, **kwargs):
        if 'embedImg' in kwargs and kwargs['embedImg'] == True:
            return cls.send_img_mail(subject, body, recipients, from_email, html_message, **kwargs)
        else:
            return super().send_email(subject, body, recipients, from_email, html_message, **kwargs)
        
        
    @classmethod
    def img_data(cls, imgPath, id):
        try:
            with open(finders.find(imgPath), 'rb') as f:
                img_data = f.read()
            img = MIMEImage(img_data)
            img.add_header('Content-ID', '<'+id+'>')
        
            return img
        except:
            return None
    @classmethod
    def embed_img(cls, message, html, balise_url):
        imgURL = balise_url.replace( "/" + settings.STATIC_URL, "")
        id = randomID(5)
        imgData=cls.img_data(imgURL, id )
        if imgData is not None:
            message.attach(imgData)
            return re.sub(re.escape(balise_url), "cid:" + id, html)
        return html
    
    @classmethod
    def send_img_mail(cls, subject, body, recipients, from_email=None, html_message=None, **kwargs):
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
        
        
        # Scrap Image balise from HMLT and embbed them if in static path
        reIm = r'<img\s+src="([^"]+)"'
        balises_img = re.findall(reIm, html_message)
        html_mod = html_message
        staticURL = "/" + settings.STATIC_URL
        for balise_src in balises_img:
            if balise_src.startswith(staticURL):
                html_mod = cls.embed_img(message, html_mod, balise_src)
        
        # attache html and send
        message.attach_alternative(html_mod, "text/html")
        response= message.send(fail_silently=False)
        return response
    
    
    
    
class UserLanguageMail(BaseMail):
    """ change render_html of base mail
    Add translation from language defined in user setting NOTIFCATION_REPORT_LANGUAGE
    NEED a user parameter in kwargs
    """
    def render_html(self, **kwargs):
        if not 'user' in kwargs:
            raise ObjectDoesNotExist("User Not defined for [SubscriptionMail]")
        user = kwargs['user']
        lang =  LMUserSetting.get_setting("NOTIFCATION_REPORT_LANGUAGE", user=user)
        cur_language = translation.get_language()
        
        try:
            translation.activate(lang)
            html = render_to_string(self.__class__.mail_template,self.context)
        finally:
            translation.activate(cur_language)
    
        if html is None:
            raise ObjectDoesNotExist("Error for language definition in [UserLanguageMail]")        
       
        return html 
    
import pandas as pd
class BodyTableMail(BaseMail):
    """ change render_body of base mail
    to transform html containign table into readable text
    using panda library    
    """
    def concatenate_tables_with_text(self, df, html_content):
        result = ""
        last_table_end = 0

        for table in df:
            table.fillna('-', inplace=True)
            table_start = html_content.find("<table", last_table_end)
            table_end = html_content.find("</table>", table_start) + len("</table>")

            # Add the text between the previous table and the current table to the result
            result += html_content[last_table_end:table_start]

            # Append the table data to the result
            result += table.to_string(index=False) + "\n\n"

            last_table_end = table_end

        # Add the remaining text after the last table
        result += html_content[last_table_end:]

        return result
    
    def render_body(self, html, **kwargs):
        tablesPD = pd.read_html(html)
        body = self.concatenate_tables_with_text(tablesPD, html)
        body = super().render_body(body, **kwargs)
        return body
    
   
    
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
from labsmanager.utils import create_dict

class SubscriptionMail(EmbedImgMail, UserLanguageMail, BodyTableMail):
    """ Class to generate and send Notification email from subscription
    NEED a user parameter in kwargs
     """
    mail_template="email/notification_email.html"
    default_subject = "Notification Report"
    

    def generate_context(self, **kwargs):
        
        super().generate_context(**kwargs)
        
        if not 'user' in kwargs:
            raise ObjectDoesNotExist("User Not defined for [SubscriptionMail]")
        user = kwargs['user']
        
        sub_enab =  LMUserSetting.get_setting("NOTIFCATION_STATUS", user=user)
        freq = LMUserSetting.get_setting("NOTIFCATION_FREQ",   user=user)
        choices=LMUserSetting.get_setting_choices("NOTIFCATION_FREQ")
        leaves_report=LMUserSetting.get_setting("NOTIFCATION_INC_LEAVE", user=user)
        leaves_timeframe=LMUserSetting.get_setting("NOTIFCATION_LEAVE_TIMEFRAME", user=user)
        inc_emp=LMUserSetting.get_setting("NOTIFCATION_EMP_INCOMMING", user=user)
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
            'report_inc_emp':inc_emp,
            'sub_freq':freq_name,
            'next_date':next_date,    
        })
        # get subscription
        subs = subscription.objects.filter(user=user.pk)
        # # get subscription
        # subs = subscription.objects.filter(user=user.pk)
        
        # for projects
        conttype_proj = ContentType.objects.get(app_label="project", model="project")
        proj_ids = subs.filter(content_type= conttype_proj).values_list("object_id")
        # projects = Project.objects.filter(pk__in = proj_ids).order_by("name")
        # fund_lines = Fund.objects.filter(project__in=proj_ids).order_by("project__name")
        
        projects = Project.get_instances_for_user('view', user).filter(pk__in = proj_ids).order_by("name")
        fund_lines = Fund.get_instances_for_user('view', user).filter(project__in=proj_ids).order_by("project__name")
        
        self.context['projects']=projects
        self.context['funds']=fund_lines
        
        for pj in projects:
            fo = get_project_fund_overviewReport_bytType(pj.pk)
            self.context['fund_o_'+str(pj.name)] = fo
        
        
        # for employees
        conttype_emp = ContentType.objects.get(app_label="staff", model="employee")
        emp_ids = subs.filter(content_type= conttype_emp).values_list("object_id")
        # employees  = Employee.objects.filter(pk__in = emp_ids).order_by("last_name")
        employees = Employee.get_instances_for_user('view', user).filter(pk__in = emp_ids).order_by("last_name")
        
        # for active contract
        # contracts = Contract.objects.filter(employee__in=emp_ids, is_active=True)
        contracts = Contract.get_instances_for_user('view', user).filter(employee__in=emp_ids, is_active=True)
        
        self.context['employees']=employees 
        self.context['contracts']= contracts
        
        # for team
        
        conttype_team = ContentType.objects.get(app_label="staff", model="team")
        team_ids  = subs.filter(content_type= conttype_team).values_list("object_id")
        teams = Team.objects.filter(pk__in = team_ids).order_by("name")
        self.context['teams']=teams 
        
        if leaves_timeframe== "current":
            slot = utils.getCurrentMonthTimeslot()
        elif leaves_timeframe== "31days":
            slot = utils.getdaysTimeslot(-1,31)
        else:
            slot = utils.getCurrentMonthTimeslot()

        self.context['days']=[slot['from'] + datetime.timedelta(days=i) for i in range((slot['to']  - slot['from'] ).days+1)]
        
        leaves_format=LMUserSetting.get_setting("NOTIFCATION_LEAVE_FORMAT", user=user)
        self.context['leave_format']=leaves_format 
        
        leaves_reportNone=LMUserSetting.get_setting("NOTIFCATION_LEAVE_REPORT_NONE", user=user)
        
        for t in teams:
            tm = TeamMate.current.filter(team=t)
            tmE = Employee.objects.filter(Q(pk__in=tm.values('employee')) | Q(pk=t.leader.pk))
            self.context['teammate_'+str(t.name)]=tmE 
            leave=Leave.objects.timeframe(slot).filter(employee__in=tmE).order_by('-end_date')   
            self.context['leave_'+str(t.name)]=leave 
            lv_list=create_dict('employee', leave)
            #add team leader and teammant not in list for calendar
            if leaves_reportNone:
                if t.leader not in lv_list:
                        lv_list[t.leader]=[]
                for tmm in tm:
                    if tmm.employee not in lv_list:
                        lv_list[tmm.employee]=[]
            self.context['leave_emp_'+str(t.name)]=lv_list 
                    
        
        if leaves_report:
            lv=Leave.objects.timeframe(slot).all().order_by('employee') 
            lv_list=create_dict('employee', lv)
               
            self.context['all_leaves']=lv 
             
            self.context['current_month']=slot['from'].strftime('%B')
            self.context['timeslot']=slot
            
            if leaves_reportNone:
                emps = Employee.objects.filter(is_active=True)
                for e in emps:
                    if e not in lv_list:
                        lv_list[e]=[]
                        
            self.context['emp_leaves']=lv_list
        if inc_emp:
            em_list = Employee.get_incomming(relativedelta(months=+2))
            self.context['inc_emp']=serializers.IncommingEmployeeSerialize(em_list, many=True).data
            
        from plugin import registry
        
        pg_context = {}
        for plugin in registry.with_mixin("mailsubscription", active=True):
            ctx = plugin.add_context(user, self.context.copy())
            pg_context[plugin.slug]=ctx
        
        self.context.update(pg_context)
        
        
        