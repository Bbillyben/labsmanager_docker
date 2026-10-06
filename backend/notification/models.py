from django.utils.translation import gettext_lazy as _
from django.db import models
from django.contrib.auth.models import User
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.utils.timezone import is_naive
from django.db.models import Q

from datetime import datetime, date, timedelta

from model_utils.managers import InheritanceManager

from .utils import check_enabled_notification_user

import logging 
logger = logging.getLogger("labsmanager")

class NotificationBase(models.Model):
    ''' Base Notification for Labs Manager, abstract class, 
    reference source object that the notification refer to*
    inclmuding a message, creation date and send date
    '''
    objects = models.Manager()
    object_inherit = InheritanceManager()
    
    class Meta:
        abstract=True
        
    source_content_type = models.ForeignKey(
        ContentType,
        on_delete=models.SET_NULL,
        related_name='notification_source',
        null=True,
        blank=True,
    )
    source_object_id = models.PositiveIntegerField(null=True, blank=True)
    source_object = GenericForeignKey('source_content_type', 'source_object_id')

   
    message = models.CharField(max_length=250, blank=True, null=True)
    creation = models.DateTimeField(auto_now_add=True)
    send = models.DateTimeField(null=True, blank=True)
    
    @property
    def done(self):
        """Return True if 'send' is not null or blank."""
        return self.send is not None and not is_naive(self.send)

class TypedNotification(models.Model):
    '''
    add an action type to notification (like add, remove, stale, complete, delete)
    to determine which type of action has trigger the notification
    '''
    class Meta:
        abstract=True
        
    type_cont=(("add",_("Add")), 
               ("rem", _("Remove")), 
               ("sta", _("Stale")),
               ("ove", _("Overdue")),
               ("com", _("Complete")),
               ("del", _("Delete")),
               ("res", _("Reschedule")),
               ("ovl", _("Overload")),
            )
    action_type = models.CharField(
        max_length=3,
        choices=type_cont,
        blank=True,
        null=True,
        default=None,   
        verbose_name=_('Status'),        
    )
    
class UserNotification(TypedNotification, NotificationBase):
    '''
    Notification with user reference
    '''
    class Meta:
        verbose_name = _("Notification")
        
     # user that receives the notification
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        verbose_name=_('User'),
        help_text=_('User'),
        null=True,
        blank=True,
    )
    
    @classmethod
    def _add_notification(cls, user, content_type, object_id, action, message):
        notif = cls(
            user = user,
            source_content_type = content_type,
            source_object_id = object_id,
            action_type = action,
            message = message,
        )
        notif.save()
        logger.debug(f' Notification created for user "{user}": {action} on {content_type} ({object_id})')
        return notif
    @classmethod
    def _update_notification(cls, user, content_type, object_id, action, message):
        
        try:
            notif = cls.objects.get(user=user, source_content_type=content_type, source_object_id=object_id, action_type=action)
            notif.user = user
            notif.source_content_type = content_type
            notif.source_object_id = object_id
            notif.action_type = action
            notif.message = message
            notif.save()
            logger.debug(f' Notification update for user "{user}": {action} on {content_type} ({object_id})')
        
        except:
            notif=None
            logger.warning(f' Unable to update notification for user "{user}": {action} on {content_type} ({object_id})')

        return notif
    
    @classmethod
    def add_notification(cls, user, instance, action, message=None, force=False, repeat_delay=0):
        '''
        Add a notification to the user notification list 
        user : user to be notified
        instance : the source instance object for the notification
        action : the action type (should be included in type_cont)
        message : the message to be display for notification (if requires)
        force : if a notification is pending, force the update of that notif, if the same notif exist, force a new one
        repeat_delay : the delay to repeat a notification (0 to disable)
        '''
        if not any(action == item[0] for item in cls.type_cont):
            logger.error(f'Action "{action}" is not a find in type of notification action')
            return 
        
        content_type = ContentType.objects.get_for_model(instance)
        
        #check if notification is enabled or not for this content type for this user
        if not check_enabled_notification_user(user, content_type):
            logger.debug(f'Notification for user {user} on type {content_type} is disabled')
            return None
        
        # findout wether a previous notification already registered
        notifs=cls.get_notifs(user, content_type, instance.pk, action)
        
        if not notifs.exists(): # if no notif exist yet => add a new one
            return cls._add_notification(user, content_type, instance.pk, action, message)
        
        if notifs.filter(send=None).exists():# if a notif pending
            if force:
                return cls._update_notification(user, content_type, instance.pk, action, message)
            else:
                logger.debug(f' Notification for user "{user}": {action} on {instance} is already pending')
                return None
                
        
        # HERE : a previous notification with same instance and action has been found, 
        # if force : new one
        if force:
            return cls._update_notification(user, content_type, instance.pk, action, message)
        
        # check if the repeat delay is due on that notification
        if repeat_delay==0:
            logger.debug(f' Notification for user "{user}": {action} on {instance} has already been send and repetition are deactivated')
            return None
        
        cdate = date.today() + timedelta(days=-repeat_delay)
        query = Q(send__gte=cdate)
        if notifs.filter(query).exists(): # if a notif has been found less than repeat delay => repeat not yet due
            logger.debug(f' Repeat Notification for user "{user}": {action} on {instance} is not due yet (delay :{repeat_delay})')
            return None
        
        # at the end, add the notification
        return cls._add_notification(user, content_type, instance.pk, action, message)

    @classmethod
    def get_notifs(cls, user, content_type, object_id, action):
        notifs = cls.objects.filter(user=user, source_content_type=content_type, source_object_id=object_id, action_type=action )
        return notifs
    @classmethod
    def is_exist(cls, user, content_type, object_id, action) -> bool:
        notifs = cls.get_notifs( user, content_type, object_id, action)
        return notifs.exists()
    
    @classmethod
    def has_been_notified(cls, user, content_type, object_id, action) -> bool:
        notifs = cls.get_notifs( user, content_type, object_id, action).filter(~Q(send=None))
        return notifs.exists()
    
    @classmethod
    def is_pending(cls, user, content_type, object_id, action) -> bool:
        notifs = cls.get_notifs( user, content_type, object_id, action).filter(send=None )
        return notifs.exists()
    