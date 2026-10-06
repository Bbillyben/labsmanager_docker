from asyncio import constants
from pydoc import doc
from .models import Project
from django.contrib.auth.models import User

from django.http import JsonResponse
from django.http import HttpResponse
import logging
logger=logging.getLogger("labsmanager")
def ajax_project(request):
    if request.method == 'GET':
        datas=request.GET

    elif request.method == 'POST':
        datas=request.POST
    else:
        raise Exception("Only get and Post are processed") 
    
    if datas['action_type'] == 'activate_project_true':
        pkU=datas['pk']
        proj = Project.objects.get(pk=pkU)
        if proj:
            proj.status = True
            proj.save()
    elif datas['action_type'] == 'activate_project_false':
        pkU=datas['pk']
        proj = Project.objects.get(pk=pkU)
        if proj:
            proj.status = False
            proj.save() 
    else:
        logger.warning("================== >>>>  AJAX STAFF COMMAND NOT FOUDN "+datas['action_type']+"  <<<< ==============================")
        
    return JsonResponse({"status":"ok,"}, safe=False)