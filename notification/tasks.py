from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required
from django.utils.translation import gettext_lazy as _

from django_q.models import Schedule
from django.shortcuts import render, HttpResponse
from django.http import JsonResponse

from allauth.account.models import EmailAddress
from datetime import datetime

from settings.models import LMUserSetting

from .models import UserNotification
from .mails import NotificationMail
from .utils import check_overdue_milestones, check_stale_milestones


import logging
logger = logging.getLogger('labsmanager')

def check_all_notification():
    logger.debug(f"[check_all_notification] called")
    check_overdue_milestones()
    check_stale_milestones()



def send_pending_notification():
    logger.debug(f"[send_pending_notification] called")
    users=UserNotification.objects.filter(send=None).values_list("user", flat=True).distinct()
    cdate = datetime.now()
    count = 0
    for user in users:
        emails= EmailAddress.objects.filter(user=user, primary=True, verified=True)
        if not emails:
            logger.error(f"Notification Error : no primary and verified Email for user {user}")
            continue
        
        mail = emails.first()
        kwargs ={'user':user, 'embedImg':True, }
        sm = NotificationMail()
        response = sm.send(mail.email , **kwargs)
        logger.debug(f" Notification Mail sending  to {mail.email} / status : {response}")
        if response ==1:
            count+=1
            uNotif = UserNotification.objects.filter(user=user, send=None)
            uNotif.update(send=cdate)
            
    return count