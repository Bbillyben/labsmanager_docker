from django.shortcuts import render
from django.http import HttpResponse
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic.base import TemplateView, View
from django.utils.translation import gettext_lazy as _
from django.utils.functional import cached_property
from django.urls import reverse
from view_breadcrumbs import BaseBreadcrumbMixin
from .models import Fund, Fund_Item
from expense.models import Expense_point, Cost_Type
from django.db.models import Value, Count
import pandas as pd
from django.contrib.contenttypes.models import ContentType
from fund.models import AmountHistory
import json

def get_fundItem_table(request, pk):
    fundP=Fund.objects.filter(pk=pk).first()
    data = {'fund': fundP}
    data['has_perm']=request.user.has_perm('fund.change_fund', fundP)
    return render(request, 'fund/fund_item_table.html', data)

def get_fundExpenseTimepoint_table(request, pk):
    fundP=Fund.objects.filter(pk=pk).first()
    data = {'fund': fundP} 
    data['has_perm']=request.user.has_perm('fund.change_fund', fundP)
    return render(request, 'expense/expense_timepoint.html', data)

def get_fundExpense_table(request, pk):
    fundP=Fund.objects.filter(pk=pk).first()
    data = {'fund': fundP} 
    data['has_perm']=request.user.has_perm('fund.change_fund', fundP)
    return render(request, 'expense/expense_list.html', data)

def get_fund_global_overview(request, pk):
    a=Fund_Item.objects.values_list('type__name', 'amount', named=False).filter(fund=pk)
    if a:
        a=a.annotate(source=Value('Fund'))
    # get cost type
    cts=Cost_Type.objects.all()
    bp = Expense_point.objects.none()
    EPa=Expense_point.objects.filter(fund=pk)
    if EPa:
        EPa = EPa.annotate(source=Value('Expense'))
        for ct in cts:
            bpT=EPa.filter(type=ct.pk).order_by('-value_date').first()
            if bpT:
                bp= bp.union(EPa.filter(pk=bpT.pk))
    
        b=bp.values_list('type__name', 'amount', 'source', named=False)
    else:
        b=None
    if a and b:
        c = a.union(b)
    elif a:
        c = a.all()
    else:
        resp='<i>'+_('No Matching Fund Item')+'</i>'
        return HttpResponse(resp)
        
    cpd=pd.DataFrame.from_records(c, columns=["type","amount","source"])
    piv=cpd.pivot_table(index="type", columns="source", values="amount", aggfunc='sum', margins=True, margins_name='Sum')
    
    data = {'df': piv, 'title':'overview', 'table_id':'fund_overview_table'}  
    
    return render(request, 'pandas/basic_table.html', data)

class RecetteGraphView(LoginRequiredMixin, View):
    template_general="project/amount_graph.html" 
    
    def get(self, request, *args, **kwargs):
        pj_pk=kwargs.get("pk", None)
        context={'data':'',
                 'type':'line',
                 'title':_("Project Expense"),
                 } 
        
        if pj_pk is None:
            return HttpResponse(_("Project Not Found"))
        
        
        qset = Fund_Item.objects.filter(fund__project=pj_pk).order_by("value_date")
        
        if not qset:
            return HttpResponse(_("No Fund found for that project"))
        
        datas=[]

        ct = ContentType.objects.get_for_model(Fund_Item)
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
        # datas= sorted(datas, key=lambda item: item['date'])
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
                 'title':_("Project Fund Overview"),
                 'domid':"recette",
                 'invert':0,
                 }  
        return render(request, self.template_general, context)

    
    
    
class FundFinderView(BaseBreadcrumbMixin, TemplateView):
    
    template_name = "fund/fund_finder.html"
    crumbs = [(_("Fund Finder"),"fund finder")]
    
        
    