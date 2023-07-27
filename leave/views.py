from django.shortcuts import render
from django.utils.translation import gettext_lazy as _
from django.http import HttpResponse

from .models import Leave_Type
from staff.models import Employee_Type, Team
# Create your views here.
import json


def main_calendar_view(request):
    leave=Leave_Type.objects.all()
    emp_types=Employee_Type.objects.all()
    team=Team.objects.all()
    print(leave)
    context={
        'leave_type':leave,
        'emp_types':emp_types,
        'team':team,
    }
    return render(request, 'calendar/main_calendar.html', context)

def main_calendar_print(request):
    context={}
    
    options={}
    options["initialView"]=request.POST["initialView"]
    options["start"]=request.POST["start"]
    options["end"]=request.POST["end"]
    options["filterResourcesWithEvents"]=request.POST["filterResourcesWithEvents"]
    options["type"]=request.POST["type"]
    options["emp_status"]=request.POST["emp_status"]
    options["team"]=request.POST["team"]
    options["showResEventRadio"]=request.POST["showResEventRadio"]
    context["options"]=options
    return render(request, 'calendar/main_calendar_print.html', context)


