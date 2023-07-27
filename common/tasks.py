from .models import subscription
from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required
from django.utils.translation import gettext_lazy as _
from django.core.exceptions import ObjectDoesNotExist


from django_q.models import Schedule

from django.shortcuts import render, HttpResponse
from django.http import JsonResponse
from settings.models import LMUserSetting

from labsmanager.mails import SubscriptionMail
from allauth.account.models import EmailAddress

import logging
logger = logging.getLogger('labsmanager')



def checkuser_notification_tasks(user):
    currSch = Schedule.objects.filter(name='send_notification_'+str(user.username))
    sub_enab =  LMUserSetting.get_setting("NOTIFCATION_STATUS", user=user)
    
    print(f' checkuser_notification_tasks / user : {user} / enabled :{sub_enab} / curr prog :{currSch}')
    if not currSch and not sub_enab:
        return
    
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
    
    usersSubs=subscription.objects.all().values_list("user", flat=True)
    usersSet = LMUserSetting.objects.filter(key__iexact="NOTIFCATION_INC_LEAVE", value="True").values_list("user", flat=True)
    users=list(usersSubs.union(usersSet))
    # users=users.distinct("user")
    
    for u_pk in users:
        user = User.objects.get(pk=u_pk)
        if not user:
            logger.error(f"Notification User {u_pk} do not exist in DB")
            continue
        checkuser_notification_tasks(user)        


def send_notification(*args, **kwargs):
    print("###############   [cdmmon.tasks.send_notification]    #######")
    pkU = kwargs.get("user_pk", None)
    if pkU == None:
        logger.error(f"Notification Send  has no user defined in kwargs : {kwargs}")
        return None    
    user = User.objects.get(pk=pkU)
    
    # find email in EmailAdress
    emails= EmailAddress.objects.filter(user=pkU, primary=True, verified=True)
    if not emails:
        response=JsonResponse({'status': 'error', 'message': _("No Primary Email for user %(user)s verified ")%({'user':user})}) 
        response.status_code = 400
        return response
    
    
    mail = emails.first()
    kwargs ={'user':user, 'embedImg':True, }
    sm = SubscriptionMail()
    response = sm.send(mail.email , **kwargs)

    logger.debug(f" Mail sending  to {user.email} / status : {response}")
    jsonResponse=JsonResponse({'status': 'success', 'message': _("Mail Send"), 'reponse':response}) 
    jsonResponse.status_code = 200
    return jsonResponse
    

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
        
    return response

@login_required
def test_check(request):  


    upk = request.GET["user"]
    user = User.objects.get(pk=upk)
    
    sm = SubscriptionMail()
    kwargs ={'user':user, 'embedImg':True}
    
    send_test = request.GET.get("mail", None)
    if send_test != None:
        sm.send(user.email, **kwargs)
    else:
        sm.generate_context(**kwargs)
    
    user = User.objects.get(pk=upk)
    return render(request=request,template_name="email/notification_email.html",context=sm.context)