from django.shortcuts import render
from django.utils.translation import gettext_lazy as _
from django.http import HttpResponse

from .models import Leave_Type
# Create your views here.



def main_calendar_view(request):
    leave=Leave_Type.objects.all()
    print(leave)
    context={
        'leave_type':leave
    }
    return render(request, 'calendar/main_calendar.html', context)