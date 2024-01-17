from django.shortcuts import render, get_object_or_404
from django.apps import apps
from django.urls import reverse
from django.utils.functional import cached_property
from django.utils.translation import gettext_lazy as _
from django.views.generic.base import TemplateView
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.contrib.contenttypes.models import ContentType
from django.http import HttpResponseNotFound
from django.db.models import F, Sum, ExpressionWrapper, IntegerField

from view_breadcrumbs import BaseBreadcrumbMixin
from labsmanager.mixin import CrumbListMixin

from project.models import Institution, Project, Institution_Participant
from fund.models import Fund_Institution, Fund
from expense.models import Contract

from .models import OrganizationInfos, ContactInfo
class OrganizationIndexView(LoginRequiredMixin, PermissionRequiredMixin, BaseBreadcrumbMixin, TemplateView):
    permission_required='common.display_infos'
    template_name = 'organization/orga_base.html'
    model = OrganizationInfos
    crumbs = [(_("Organization"),"organization")]
    
    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(**kwargs).copy()
        ctI = ContentType.objects.get_for_model(Institution)
        context['type_I'] = {
            'app':ctI.app_label,
            'model':ctI.model,
        }
        ctF = ContentType.objects.get_for_model(Fund_Institution)
        context['type_F'] = {
            'app':ctF.app_label,
            'model':ctF.model,
        }
        return context
class InstitutionView(LoginRequiredMixin, PermissionRequiredMixin, CrumbListMixin, BaseBreadcrumbMixin, TemplateView):
    permission_required='common.display_infos'
    template_name = 'organization/institution_single.html'
    crumbListPerm=('common.display_infos',)
    reverseURL="orga_single"
    names_val=['short_name',]
    
    app = None
    model = None
    id = None
    model_class = None
    orga = None
    
    @cached_property
    def crumbs(self, **kwargs):
        return [(_("Organization"),reverse("orga_index"),) ,
                (str(self.construct_crumb()) ,  reverse("orga_single", kwargs={'pk':'0', 'app':self.app, 'model':self.model} ) ),
                ]

    def construct_crumb(self):
        return self.orga

    def get_context_data(self, **kwargs):
        """Returns custom context data for the Employee view:
            - employee : the employee corresponding
        """
        context = super().get_context_data(**kwargs).copy()
        if not self.id:
            return context

        context['orga'] = self.orga
        context['type'] = {
            'app':self.app,
            'model':self.model,
        }
        context['urls']={               
            }
        if self.request.user.is_staff:
            context['urls']['admin']=reverse("admin:"+self.app+"_"+self.model+"_change", kwargs={'object_id':id} )
        if self.request.user.has_perm(self.app+".change_"+self.model):
            context['urls']['change']=reverse("update_"+self.app+"_"+self.model, kwargs={'pk':self.id} )

        return context

    def get(self, request, *args, **kwargs):     
        self.app=kwargs.get("app", None)
        self.model=kwargs.get("model", None)
        self.id=kwargs.get("pk", None)
        self.model_class = apps.get_model(app_label=self.app, model_name=self.model)
        self.orga = get_object_or_404(self.model_class, pk=self.id)
        if not self.orga:
            return HttpResponseNotFound("App or Model not set")
        
        self.crumbListQuerySet = self.model_class.objects.all()
        self.default_kwargs={'app':self.app, 'model':self.model}
        return super().get(request, args, kwargs)

# ------------------------- FOR Organisation General -------------------------- 
# -----------------------------------------------------------------------------

def get_orga_resume(request, app, model, pk):
    model_class = apps.get_model(app_label=app, model_name=model)
    
    orga = get_object_or_404(model_class, pk=pk)
    data = {'orga': orga}
    ## Info supp
    # contracts 
    if model_class == Institution:
        # ip = Fund.objects.filter(institution=orga).values('project')
        fu=Fund.objects.filter(institution=orga)
        
    elif model_class == Fund_Institution:
        fu=Fund.objects.filter(funder=orga)
        ip = fu.values('project')
        
    coT = Contract.objects.filter(fund__in=fu)
    coC = Contract.current.filter(fund__in=fu)
    data['contract']={
        'total':coT.count(),
        'total_active':coT.filter(is_active=True).count(),
        'total_MM':coT.annotate(
                man_month_sum=ExpressionWrapper(
                    F('end_date__year') - F('start_date__year'),
                    output_field=IntegerField()
                ) * 12 + F('end_date__month') - F('start_date__month')
            ).aggregate(Sum('man_month_sum'))["man_month_sum__sum"],
        'current':coC.count(),
        'current_active':coC.filter(is_active=True).count(),
        'current_MM':coC.annotate(
                man_month_sum=ExpressionWrapper(
                    F('end_date__year') - F('start_date__year'),
                    output_field=IntegerField()
                ) * 12 + F('end_date__month') - F('start_date__month')
            ).aggregate(Sum('man_month_sum'))["man_month_sum__sum"],
    }   
    
    # projects 
    if model_class == Institution:
        ip1 = Institution_Participant.objects.filter(institution=orga).values('project')
        ip2 = Fund.objects.filter(institution=orga).values('project')
        ip= ip1.union(ip2)
        # fu=Fund.objects.filter(project__in=ip)
        
    
    proj = Project.objects.filter(pk__in=ip)
    
    data['project']={
        'total':proj.count(),
        'open':proj.filter(status=True).count(),
        'total_amount':fu.aggregate(Sum('amount'))["amount__sum"],
        'total_avail':fu.aggregate(avail=Sum(F('amount') + F('expense')))['avail'],
        'total_avail_f':fu.aggregate(avail_f=Sum(F('amount_f') + F('expense_f')))['avail_f'],
        'open_amount':fu.filter(project__status=True).aggregate(Sum('amount'))["amount__sum"],
        'open_avail':fu.filter(project__status=True).aggregate(avail=Sum(F('amount') + F('expense')))['avail'],
        'open_avail_f':fu.filter(project__status=True).aggregate(avail_f=Sum(F('amount_f') + F('expense_f')))['avail_f'],
        
    }
        
    
    
    
    
    
    return render(request, 'organization/orga_desc_table.html', data)


def get_orga_info(request, app, model, pk):
    ct = ContentType.objects.get(app_label=app, model=model)
    info = OrganizationInfos.objects.filter(content_type = ct, object_id = pk)
    data = {'info': info} 
    data['object_id']=pk
    data['type'] = {
            'app':ct.app_label,
            'model':ct.model,
        }

    return render(request, 'organization/orga_info_table.html', data)

# ------------------------- FOR Contact -------------------------- 
# ---------------------------------------------------------------
def get_orga_contact_info(request, id):
    ci = ContactInfo.objects.filter(contact=id)
    data={'infos_contact':ci}
    data['object_id']=id
    return render(request, 'organization/contact_info_table.html', data)
    