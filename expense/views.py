from django.shortcuts import render
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic.base import TemplateView, View
from django.utils.translation import gettext_lazy as _
from django.utils.functional import cached_property
from django.urls import reverse
from view_breadcrumbs import BaseBreadcrumbMixin
from .models import Contract, Contract_expense, Expense_point
from django.http import HttpResponse, JsonResponse
from .serializers import ProjectExpensePointGraphSerializer

class ContractIndexView(LoginRequiredMixin, BaseBreadcrumbMixin, TemplateView):
    template_name = 'expense/contract_base.html'
    home_label = '<i class="fas fa-bars"></i>'
    model = Contract
    crumbs = [("Contracts","contracts")]
    


class ExpenseGraphView(LoginRequiredMixin, View):
    template_general="project/project_consumption_graph.html" 
    
    def get(self, request, *args, **kwargs):
        pj_pk=kwargs.get("pk", None)
        context={'data':'',
                 'type':'line',
                 'title':_("Project Expense"),
                 } 
        
        if pj_pk is None:
            return HttpResponse(_("Project Not Found"))
        
        
        qset = Expense_point.objects.filter(fund__project=pj_pk).order_by("value_date")
        
        if not qset:
            return HttpResponse(_("No expense found for that project"))
        
        datas=[]
        counter={}
        for ep in qset:
            en_item=ep.fund.pk
            type_item=ep.type.pk
            tid=str(en_item)+"-"+str(type_item)
            if tid in counter:
                expense=ep.amount-counter[tid]
            else:
                expense=ep.amount
                
            counter[tid]=ep.amount
            datas.append(
                {
                    'date':ep.value_date.isoformat(),
                    'funder':ep.fund.funder.short_name,
                    'institution':ep.fund.institution.short_name,
                    'type':ep.type.short_name,
                    'ref':ep.fund.ref,
                    'amount':str(expense),
                    
                }
            )
            
        import pandas as pd
        df = pd.DataFrame(datas)
        dataTosend=df.to_json(orient='table')
    
        context={'data':dataTosend,
                 'type':'line',
                 'title':_("Project Expense Overview"),
                 }  
        return render(request, self.template_general, context)

# Create your views here.

def get_contractExpense_table(request, pk):
    cont=Contract.objects.filter(pk=pk).first()
    data = {'contract': cont}   
    return render(request, 'expense/contract_item_expense.html', data)