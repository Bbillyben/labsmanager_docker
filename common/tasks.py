from .models import subscription
from django.contrib.auth.models import User
from django.utils.translation import gettext_lazy as _
from django.core.exceptions import ObjectDoesNotExist


from django_q.models import Schedule

from django.shortcuts import render, HttpResponse
from settings.models import LMUserSetting

import logging
logger = logging.getLogger('labsmanager')



def checkuser_notification_tasks(user):
    currSch = Schedule.objects.filter(name='send_notification_'+str(user.username))
    sub_enab =  LMUserSetting.get_setting("NOTIFCATION_STATUS", user=user)
    
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

from labsmanager.mails import SubscriptionMail

def send_notification(*args, **kwargs):
    print("###############   [cdmmon.tasks.send_notification]    #######")
    pkU = kwargs.get("user_pk", None)
    if pkU == None:
        logger.error(f"Notification Send  has no user defined in kwargs : {kwargs}")
        return None    
    user = User.objects.get(pk=pkU)
    
    kwargs ={'user':user, }
    sm = SubscriptionMail()
    response = sm.send(user.email,True , **kwargs)

    logger.debug(f" Mail sending  to {user.email} / status : {response}")
    return response
    

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
    user = User.objects.get(pk=upk)
    
    sm = SubscriptionMail()
    kwargs ={'user':user, }
    
    send_test = request.GET.get("mail", None)
    if send_test != None:
        sm.send(user.email,True , **kwargs)
    else:
        sm.generate_context(**kwargs)
    
    user = User.objects.get(pk=upk)
    return render(request=request,template_name="email/notification_email.html",context=sm.context)