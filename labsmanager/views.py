from django.shortcuts import render
from django.template.loader import render_to_string
from django.http import HttpResponse, Http404
from django.template.response import SimpleTemplateResponse
from django.views.generic.base import TemplateView
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.template import RequestContext
from django.shortcuts import render, redirect
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import F


from staff.models import Employee_Type
from fund.models import Cost_Type
from expense.models import Contract_type, Contract
from fund.models import Fund_Institution
from project.models import Institution
from leave.models import Leave_Type
# from allauth.account.views import LoginView
# Create your views here.

from django.contrib.auth.decorators import user_passes_test
from labsmanager import settings
import os



class redirectIndexView(LoginRequiredMixin, TemplateView):
    template_name = 'labmanager/index.html' #'labmanager/index.html'
    def get(self, request, *args, **kwargs): ## Redirect to dash board for the moment
        return redirect('dashboard')
    
class IndexView(LoginRequiredMixin, TemplateView):
    """View for index page."""
    template_name = 'labmanager/index.html' #'labmanager/index.html'
    
    # def get(self, request, *args, **kwargs): ## Redirect to dash board for the moment
    #     return redirect('dashboard')
    


def is_admin(user):
    return user.is_authenticated and user.is_superuser

@user_passes_test(is_admin, login_url="/index/")
def serve_protected_media(request, path):
    """ View specific to serve report file stored in MEDIA_ROOT/report/... to admin only
    """
    file_path = os.path.join(settings.MEDIA_ROOT, 'report/'+path)
    if os.path.exists(file_path):
        with open(file_path, 'rb') as file:
            return HttpResponse(file.read(), content_type='application/octet-stream')
    else:
        raise Http404

#   Get type list for filtering tables across labsmanager
from django.db.models import Count, Value, CharField
from django.db.models.functions import Concat
def get_filters_lists(request, *args, **kwargs):
    data={}
    data['codes']=[]
    # for employee type list, use shortname
    empType = Employee_Type.objects.all().values(key=F('pk'), value=F('name'))
    data['codes'].append({
        'name':'employee_status',
        'data':empType,
    })
    
    # for cost type 
    costType = Cost_Type.objects.all().values(key=F('pk'), value=F('name'), num_parent=F('level'))
    data['codes'].append({
        'name':'cost_type',
        'data':costType,
    })
    
    #for contract typ
    contType=Contract_type.objects.all().values(key=F('pk'), value=F('name'))
    data['codes'].append({
        'name':'contract_type',
        'data':contType,
    })
    contStatus = [{'key': key, 'value': value} for key, value in Contract.type_cont]
    # for contract status
    data['codes'].append({
        'name':'contract_status',
        'data':contStatus,
    })
    # for funder
    fundIns=Fund_Institution.objects.all().values(key=F('pk'), value=F('name'))
    data['codes'].append({
        'name':'fund_institution',
        'data':fundIns,
    })
    
    # for Institution
    inst=Institution.objects.all().values(key=F('pk'), value=F('short_name'))
    data['codes'].append({
        'name':'institution',
        'data':inst,
    })
    
    # for leaves
    l_type=Leave_Type.objects.all().values(key=F('pk'), value=F('name'), num_parent=F('level'))
    
    data['codes'].append({
        'name':'leave_type',
        'data':l_type,
    })
    
    return render_to_string('status_codes.js', data)
    