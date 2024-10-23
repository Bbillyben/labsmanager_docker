from pydoc import doc
from .models import Employee, Employee_Status, Employee_Type
from django.contrib.auth.models import User

from django.http import JsonResponse
from django.http import HttpResponse
import logging
logger=logging.getLogger("labsmanager")
def ajax_staff(request):
    
    if request.method == 'GET':
        datas=request.GET

    elif request.method == 'POST':
        datas=request.POST
    else:
        raise Exception("Only get and Post are processed") 
    
    if datas['action_type'] == 'activate_user_true':
        pkU=datas['pk']
        user = Employee.objects.get(pk=pkU)
        if user:
            user.is_active = True
            user.save()
    elif datas['action_type'] == 'activate_user_false':
        pkU=datas['pk']
        user = Employee.objects.get(pk=pkU)
        if user:
            user.is_active = False
            user.save() 
    else:
        logger.warning("================== >>>>  AJAX STAFF COMMAND NOT FOUDN "+datas['action_type']+"  <<<< ==============================")
        
    return JsonResponse({"status":"ok,"}, safe=False)