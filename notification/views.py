from django.shortcuts import render,HttpResponse
from django.http import JsonResponse
from django.utils.translation import gettext_lazy as _
from .utils import check_stale_milestones, check_overdue_milestones
# Create your views here.

import logging 
logger = logging.getLogger("labsmanager")

def launch_check_notification(request):
    logger.debug("--- call launch_check_notification")
    c1 = check_stale_milestones()
    c2 = check_overdue_milestones()
    if c1+c2 ==0:
        res_str=_("No Notification added")
    elif c1>0 and c2>0:
        res_str=_("%(stale)s stale and %(overdue)s milestones notifications have been added")%({"stale":c1, "overdue":c2})
    else:
        res_str=str(c1+c2) + (_(" stale") if c1>0 else _(" overdue")) +_(" milestone notification added")
    data={
        "response":res_str,
    }
    return JsonResponse(data)

from .tasks import send_pending_notification
def send_all_pending_notification(request):
    logger.debug("--- call send_all_pending_notification")
    response = send_pending_notification()
    res_str=_("%s Notification have been sent")%(response)
    data={
        "response":res_str,
    }
    return JsonResponse(data)