from http.client import HTTPResponse
from django.http import HttpResponse, JsonResponse
from django.shortcuts import render

from .models import Project
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic.base import TemplateView
from django.utils.translation import gettext_lazy as _
from django.utils.functional import cached_property
from django.urls import reverse
from view_breadcrumbs import BaseBreadcrumbMixin
from fund.models import Fund, Fund_Item, Cost_Type
from expense.models import Expense_point
from django.db.models import Value, Count
import pandas as pd
import json

from labsmanager.pandas_utils import PDUtils
from labsmanager.mixin import CrumbListMixin
class ProjectIndexView(LoginRequiredMixin, BaseBreadcrumbMixin, TemplateView):
    template_name = 'project/project_base.html'
    model = Project
    crumbs = [("Project","project")]
    
    
    
class ProjectView(LoginRequiredMixin, CrumbListMixin, BaseBreadcrumbMixin, TemplateView):
    template_name = 'project/project_single.html'
    model = Project
    # crumbs = [("Project","project")]
    # for CrumbListMixin
    reverseURL="project_single"
    crumbListQuerySet=Project.objects.filter(status=True)
    names_val=['name']
    
    @cached_property
    def crumbs(self):
        return [("Project","./",) ,
                (str(self.construct_crumb()) ,  reverse("project_single", kwargs={'pk':'4'} ) ),
                ]

    def construct_crumb(self):
        proj = Project.objects.get(pk=self.kwargs['pk'])
        return proj
    
    def get_context_data(self, **kwargs):
        """Returns custom context data for the Employee view:
            - employee : the employee corresponding
        """
        context = super().get_context_data(**kwargs).copy()

        if not 'pk' in kwargs:
            return context

        id=kwargs.get("pk", None)
        proj = Project.objects.filter(pk=id)
        context['project'] = proj.first()

        # View top-level categories
        return context


def get_project_resume(request, pk):
    proj = Project.objects.filter(pk=pk).first()
    data = {'project': proj}
    
    return render(request, 'project/project_desc_table.html', data)

def get_project_fund_overview(request, pk):
    fund=Fund.objects.filter(project=pk).values("pk")
    
    # get funitem related to funds
    a=Fund_Item.objects.filter(fund__in=fund)
    if a:
        a=a.values_list('fund__funder__short_name','fund__institution__short_name', 'fund__ref', 'type__name', 'amount', named=False)
        a=a.annotate(source=Value('Budget'))
        
    # get expense time poitn from related fund
    fuov=Expense_point.last.fund(fund)
    b=None
    if fuov:
        b=fuov.values_list('fund__funder__short_name','fund__institution__short_name','fund__ref', 'type__name', 'amount',  named=False).annotate(source=Value('Expense'))
        
    # b = Expense_point.objects.none()
    # for fu in fund:
    #     # ExpensePointItems=Expense_point.objects.filter(fund__pk=fu['pk']).annotate(source=Value('Expense'))
    #     # fuov=Expense_point.get_lastpoint_by_fund_qs(ExpensePointItems)
    #     fuov=Expense_point.last.fund(fu['pk']).annotate(source=Value('Expense'))
    #     if fuov:
    #         b=b.union(fuov)
    # if b:
    #     b=b.values_list('fund__funder__short_name','fund__institution__short_name','fund__ref', 'type__name', 'amount', 'source', named=False)
    #     # b=b.annotate(source=Value('Expense'))
  
    if a and b:
        c = a.union(b)
    elif a:
        c = a.all()
    else:
        resp='<i>'+_('No Matching Fund Item')+'</i>'
        return HttpResponse(resp)   
    
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
    
    # out.loc['Column_Total']= out.sum(numeric_only=True, axis=0)
    # out.loc[:,'Row_Total'] = out.sum(numeric_only=True, axis=1)
    
    PDUtils.applyColumnFormat(out, PDUtils.moneyFormat)
    # out.style.apply(PDUtils.highlight_max)
    out.style.applymap(PDUtils.style_negative, props='color:red;')
    
    table=PDUtils.getBootstrapTable(out)
      
    data = {'table':table}
    
    return render(request, 'pandas/panda_table_cpx.html', data)