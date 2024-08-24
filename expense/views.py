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
from django.contrib.contenttypes.models import ContentType
from fund.models import AmountHistory

class ContractIndexView(LoginRequiredMixin, BaseBreadcrumbMixin, TemplateView):
    template_name = 'expense/contract_base.html'
    home_label = '<i class="fas fa-bars"></i>'
    model = Contract
    crumbs = [(_("Contracts"),"contracts")]
    


class ExpenseGraphView(LoginRequiredMixin, View):
    template_general="project/amount_graph.html" 
    
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
        
 
        ct = ContentType.objects.get_for_model(Expense_point)
        qsetH=AmountHistory.objects.filter(content_type=ct, object_id__in=qset.values("pk")).order_by("value_date")
        for e in qsetH:
            ep=e.content_object
            en_item=ep.fund.pk
            type_item=ep.type.pk
            tid=str(en_item)+"-"+str(type_item)

           
            datas.append(
                {
                    'tid':tid,
                    'date':e.value_date.isoformat(),
                    'funder':ep.fund.funder.short_name,
                    'institution':ep.fund.institution.short_name,
                    'type':ep.type.short_name,
                    'ref':ep.fund.ref,
                    'amount':'',
                    'total':e.amount,
                    
                }
            )
        # sort
        #datas= sorted(datas, key=lambda item: item['date'])
        counter={}
        for it in datas:
            tid=it['tid']
            if tid in counter:
                expense=it['total']-counter[tid]
            else:
                expense=it['total']
            counter[tid]=it['total']
            it['amount']=str(expense)
            
        import pandas as pd
        df = pd.DataFrame(datas)
        dataTosend=df.to_json(orient='table')
    
        context={'data':dataTosend,
                 'type':'line',
                 'title':_("Project Expense Overview"),
                 'domid':"expense",
                 'invert':1,
                 }  
        return render(request, self.template_general, context)

# Create your views here.

def get_contractExpense_table(request, pk):
    cont=Contract.objects.filter(pk=pk).first()
    data = {'contract': cont}   
    data['has_perm']=request.user.has_perm('expense.change_contract_expense', cont)
    return render(request, 'expense/contract_item_expense.html', data)