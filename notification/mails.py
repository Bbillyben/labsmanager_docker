from django.core.exceptions import ObjectDoesNotExist
from django.contrib.auth.models import User
from labsmanager.mails import EmbedImgMail, BodyTableMail,UserLanguageMail
from settings.models import LMUserSetting

from .models import UserNotification

class NotificationMail(EmbedImgMail, UserLanguageMail, BodyTableMail):
    """ Class to generate and send Notification email from generated UserNotification
    NEED a user parameter in kwargs
     """
    mail_template="email/usernotification_email.html"
    default_subject = "Notification Report"
    def generate_context(self, **kwargs):
        
        super().generate_context(**kwargs)
        if not 'user' in kwargs:
            raise ObjectDoesNotExist("User Not defined for [SubscriptionMail]")
        user_ID = kwargs['user']
        user = User.objects.get(pk=user_ID)
        
        sub_enab =  LMUserSetting.get_setting("NOTIFCATION_STATUS", user=user)
        milestone_enab =  LMUserSetting.get_setting("NOTIFICATION_ENDPOINTS_MILESTONES", user=user)
        milestone_stale =  LMUserSetting.get_setting("NOTIFICATION_ENDPOINTS_MILESTONES_STALE", user=user)
        milestone_repeat =  LMUserSetting.get_setting("NOTIFICATION_ENDPOINTS_MILESTONES_REPEAT", user=user)
        participant_enab =  LMUserSetting.get_setting("NOTIFICATION_PROJECT_PARTICIPANT", user=user)
        
        self.context.update({
            'user':user,
            'sub_status':sub_enab,
            'milestone_enab':milestone_enab,
            'milestone_stale':milestone_stale,
            'milestone_repeat':milestone_repeat,
            'participant_enab':participant_enab,    
        })
        # get all notification and separate them by content_type of source object
        userNote = UserNotification.objects.filter(user = user)
        notif={}
        for note in userNote:
            key = ("%s_%s")%(note.source_content_type.app_label, note.source_content_type.model)
            if key not in notif:
                notif[key]=[]
            notif[key].append(note)
        self.context["notification"]=notif
        
        
        
        
        from plugin import registry
        pg_context = {}
        for plugin in registry.with_mixin("mailsubscription", active=True):
            ctx = plugin.add_context(user, self.context.copy())
            pg_context[plugin.slug]=ctx
        
        self.context.update(pg_context)