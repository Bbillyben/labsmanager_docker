from django.contrib.auth.decorators import permission_required
from http.client import HTTPResponse
from django.http import HttpResponse, JsonResponse
from django.shortcuts import render

from .models import Project, GenericInfoProject
from .forms import GenericInfoProjectForm
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.views.generic.base import TemplateView
from django.utils.translation import gettext_lazy as _
from django.utils.functional import cached_property
from django.urls import reverse
from django.http import HttpResponseRedirect 
from view_breadcrumbs import BaseBreadcrumbMixin
from fund.models import Fund, Fund_Item, Cost_Type
from expense.models import Expense_point
from django.db.models import Value, Count
import pandas as pd
import json

from labsmanager.pandas_utils import PDUtils
from labsmanager.mixin import CrumbListMixin

from settings.models import LMProjectSetting

class ProjectIndexView(LoginRequiredMixin, BaseBreadcrumbMixin, TemplateView):
    template_name = 'project/project_base.html'
    model = Project
    crumbs = [(_("Project"),"project")]
    
    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return self.handle_no_permission()
        
        if request.user.is_staff or request.user.has_perm('project.view_project') or request.user.has_perm('common.project_list') :
            return super().dispatch(request, *args, **kwargs)
        return HttpResponseRedirect(reverse('project_index'))
    
    
    
class ProjectView(LoginRequiredMixin, CrumbListMixin, BaseBreadcrumbMixin, TemplateView):
    template_name = 'project/project_single.html'
    model = Project
    
    # for CrumbListMixin
    reverseURL="project_single"
    crumbListQuerySet=Project.objects.filter(status=True)
    names_val=['name']
    crumbListPerm=['project.view_project']
    
    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return self.handle_no_permission()
        
        if request.user.is_staff or request.user.has_perm('project.view_project'):
            return super().dispatch(request, *args, **kwargs)
        
        proj = Project.objects.get(pk=kwargs['pk'])
        if request.user.has_perm("project.view_project", proj):
            return super().dispatch(request, *args, **kwargs)
        else:
            return HttpResponseRedirect(reverse('project_index'))
        
    @cached_property
    def crumbs(self):
        return [(_("Project"),"./",) ,
                (str(self.construct_crumb()) ,  reverse("project_single", kwargs={'pk':'0'} ) ),
                ]

    def construct_crumb(self):
        proj = Project.objects.get(pk=self.kwargs['pk'])
        return proj
    
    def get_context_data(self, **kwargs):
        """Returns custom context data for the Project view:
            - project : the project corresponding
            -settings
        """
        context = super().get_context_data(**kwargs).copy()

        if not 'pk' in kwargs:
            return context

        id=kwargs.get("pk", None)
        proj = Project.objects.filter(pk=id).first()
        context['project'] = proj
        
        # for settings
        settings = LMProjectSetting.objects.filter(project=proj).values('key', 'value')
        context['settings'] =  {item['key']: item['value'] for item in settings}
       
        
        return context
    



def get_project_resume(request, pk):
    proj = Project.objects.filter(pk=pk).first()
    data = {'project': proj}
    
    return render(request, 'project/project_desc_table.html', data)



def get_project_fund_panda(pk):
    fund=Fund.objects.filter(project=pk)#.values("pk")
    
    # get funitem related to funds
    a=Fund_Item.objects.filter(fund__in=fund)
    if a:
        a=a.values_list('fund__funder__short_name','fund__institution__short_name', 'fund__ref', 'type__name', 'amount', named=False)
        a=a.annotate(source=Value('Budget'))
        
    # get expense time poitn from related fund
    fuov=Expense_point.objects.filter(fund__in=fund) #.last.fund(fund)
    b=None
    if fuov:
        b=fuov.values_list('fund__funder__short_name','fund__institution__short_name','fund__ref', 'type__name', 'amount',  named=False).annotate(source=Value('Expense'))
        
  
    if a and b:
        c = a.union(b)
    elif a:
        c = a.all()
    else:
        return None
    
    cpd=pd.DataFrame.from_records(c, columns=['funder','institution', 'ref', "type","amount","source"])
    cpd["fund"]=cpd['funder']+" - "+cpd['institution']+ " ("+cpd['ref']+')'
    
    piv=cpd.pivot_table(index="type", 
                        columns=["fund","source"], 
                        values="amount", 
                        aggfunc='sum', 
                        margins=True, 
                        margins_name='Sum',
    )
    piv = piv.rename_axis(None, axis=0)  
    dfs = [] 
    for c in piv.columns.get_level_values(0).unique():
        if not c =="Sum":
            s = piv.loc[:, c].sum(axis=1, skipna=True)
            dfs.append(pd.DataFrame(s, index=s.index, columns=[(c, f"Total")]))
    # concat them together, sort the columns:
    out = pd.concat([piv, pd.concat(dfs, axis=1)], axis=1)
    # out.loc['Column_Total']= out.sum(numeric_only=True, axis=0)
    # out.loc[:,'Row_Total'] = out.sum(numeric_only=True, axis=1)
    out = out[sorted(out.columns)]
    return out
    
    
    
    
def get_project_fund_overviewReport(pk):
    out = get_project_fund_panda(pk)
    if out is None:
        return '<i>'+_('No Matching Fund Item')+'</i>'

    PDUtils.applyColumnFormat(out, PDUtils.moneyFormat)
    # out.style.apply(PDUtils.highlight_max)
    out.style.applymap(PDUtils.style_negative, props='color:red;')
    
    return out.to_json()
    
    
    
def get_project_fund_overview(request, pk):
    
    out = get_project_fund_panda(pk)
    if out is None:
        resp='<i>'+_('No Matching Fund Item')+'</i>'
        return HttpResponse(resp)   
    
    # out.loc['Column_Total']= out.sum(numeric_only=True, axis=0)
    # out.loc[:,'Row_Total'] = out.sum(numeric_only=True, axis=1)
    
    PDUtils.applyColumnFormat(out, PDUtils.moneyFormat)
    # out.style.apply(PDUtils.highlight_max)
    out.style.applymap(PDUtils.style_negative, props='color:red;')
    
    table=PDUtils.getBootstrapTable(out)
      
    data = {'table':table}
    
    return render(request, 'pandas/panda_table_cpx.html', data)

from django.db.models import Sum
from django.db.models import F  

def get_project_fund_overviewReport_bytType(pk):
    fund=Fund.objects.filter(project=pk)
    a=Fund_Item.objects.filter(fund__in=fund)
    if not a:
        return None
    
    a = a.values('type').annotate(
        type_name=F('type__name'), 
        type_focus=F('type__in_focus'), 
        type_count=Count('type'), 
        total_amount=Sum('amount'),
        total_expense=Sum('expense'),
        total_available = F("total_amount")+F("total_expense"),
        )
    return a

def get_fund_overviewReport_bytType(pk):
    a=Fund_Item.objects.filter(fund=pk)
    if not a:
        return None
    
    a = a.values('type').annotate(
        type_name=F('type__name'), 
        type_focus=F('type__in_focus'), 
        type_count=Count('type'), 
        total_amount=Sum('amount'),
        total_expense=Sum('expense'),
        total_available = F("total_amount")+F("total_expense"),
        )
    return a

## Get the project info table
def get_project_info_table(request, pk):
    info=GenericInfoProject.objects.filter(project__pk=pk)
    project = Project.objects.filter(pk = pk).first() # required for perm rules
    return render(request, 'project/project_info_table.html', {'infoProject': info, 'project':project})