from django.shortcuts import render, HttpResponse
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic.base import TemplateView
from django.utils.translation import gettext_lazy as _
from view_breadcrumbs import BaseBreadcrumbMixin
from django.urls import reverse, reverse_lazy

from .models import LMUserSetting

from fund.models import Cost_Type, Fund_Institution
from staff.models import Employee_Type, GenericInfoType
from project.models import Institution, GenericInfoTypeProject

from common.models import favorite, subscription

class SettingsView(LoginRequiredMixin, BaseBreadcrumbMixin, TemplateView):
    template_name = 'settings/settings.html'
    home_label = '<i class="fas fa-bars"></i>'
    model = LMUserSetting
    crumbs = [(_("Settings"),"settings")]
    
class SettingList_cost_type(LoginRequiredMixin, TemplateView):
    template_name = 'settings/setting_table.html'
    model = Cost_Type
    
    def get(self,request):
        # print("[SettingList_cost_type] - get")
        context={
            'url':reverse_lazy("api:settinglist-costtype"),
            'title':_('Cost Type'),
            'columns':[
                {'name':_('name'),'item':'name','formatter':'treeNameFormatter',},
                {'name':_('Short name'),'item':'short_name'},
                {'name':_('In Focus'),'item':'in_focus', 'formatter':'basicBoolean'},
            ], 
            'action':{
            },
            'options':{
            },         
        }
        if request.user.has_perm("fund.change_cost_type"):
            context["action"]["update"] = "update_costtype"
        if request.user.has_perm("fund.add_cost_type"):
            context["action"]["add"] = reverse('add_costtype')
        if request.user.is_staff :
            context["action"]["admin"] = 'admin:fund_cost_type_change'
        
        return render(request=request,template_name=self.template_name,context=context)
    
class SettingList_fundInstitution_type(LoginRequiredMixin, TemplateView):
    template_name = 'settings/setting_table.html'
    model = Fund_Institution
    
    def get(self,request):
        # print("[SettingList_fundInstitution_type] - get")
        context={
            'url':reverse_lazy("api:settinglist-fundinstitution"),
            'title':_('Fund Institution'),
            'columns':[
                {'name':_('name'),'item':'name',},
                {'name':_('Short name'),'item':'short_name'},
            ], 
            'action':{
            },
            'options':{
            },         
        }
        if request.user.has_perm("fund.change_fund_institution"):
            context["action"]["update"] = "update_fundinstitution"
        if request.user.has_perm("fund.add_fund_institution"):
            context["action"]["add"] = reverse('add_fundinstitution')
        if request.user.is_staff :
            context["action"]["admin"] = 'admin:fund_fund_institution_change'
        
        return render(request=request,template_name=self.template_name,context=context)
    
from expense.models import Contract_type
class SettingList_Contract_type(LoginRequiredMixin, TemplateView):
    template_name = 'settings/setting_table.html'
    model = Contract_type
    
    def get(self,request):
        context={
            'url':reverse_lazy("api:settinglist-contracttype"),
            'title':_('Contract Type'),
            'columns':[
                {'name':_('name'),'item':'name',},
            ], 
            'action':{
            },
            'options':{
            },         
        }
        if request.user.has_perm("expense.change_contract_type"):
            context["action"]["update"] = "update_contract_type"
        if request.user.has_perm("expense.add_contract_type"):
            context["action"]["add"] = reverse('add_contracttype')
        if request.user.is_staff :
            context["action"]["admin"] = 'admin:expense_contract_type_change'
        
        return render(request=request,template_name=self.template_name,context=context)
    
from leave.models import Leave_Type
class SettingList_Leave_type(LoginRequiredMixin, TemplateView):
    template_name = 'settings/setting_table.html'
    model = Leave_Type
    
    def get(self,request):
        context={
            'url':reverse_lazy("api:settinglist-leavetype"),
            'title':_('Leave Type'),
            'columns':[
                {'name':_('name'),'item':'name','formatter':'treeNameFormatter',},
                {'name':_('Short name'),'item':'short_name'},
                {'name':_('Color'),'item':'color', 'formatter':'colorFormatter',},
            ], 
            'action':{
            },
            'options':{
            },         
        }
        if request.user.has_perm("leave.change_leave_type"):
            context["action"]["update"] = "update_leave_type"
        if request.user.has_perm("leave.add_leave_type"):
            context["action"]["add"] = reverse('add_leave_type')
        if request.user.is_staff :
            context["action"]["admin"] = 'admin:leave_leave_type_change'
        
        return render(request=request,template_name=self.template_name,context=context)
    
       

class SettingList_Institution(LoginRequiredMixin, TemplateView):
    template_name = 'settings/setting_table.html'
    model = Institution
    
    def get(self,request):
        context={
            'url':reverse_lazy("api:settinglist-projectinstitution"),
            'title':_('Institution'),
            'columns':[
                {'name':_('name'),'item':'name',},
                {'name':_('Short name'),'item':'short_name'},
                {'name':_('Adress'),'item':'adress'},
            ], 
            'action':{
            },
            'options':{
            },         
        }
        if request.user.has_perm("project.change_institution"):
            context["action"]["update"] = "update_institution_direct"
        if request.user.has_perm("project.add_institution"):
            context["action"]["add"] = reverse('add_institution_direct')
        if request.user.is_staff :
            context["action"]["admin"] = 'admin:project_institution_change'
        
        return render(request=request,template_name=self.template_name,context=context)
    
    

class SettingList_Employee_Type(LoginRequiredMixin, TemplateView):
    template_name = 'settings/setting_table.html'
    model = Employee_Type
    
    def get(self,request):
        context={
            'url':reverse_lazy("api:settinglist-employeetype"),
            'title':_('Employee Type'),
            'columns':[
                {'name':_('name'),'item':'name',},
                {'name':_('Short name'),'item':'shortname'},
            ], 
            'action':{
            },
            'options':{
            },         
        }
        if request.user.has_perm("staff.change_employee_type"):
            context["action"]["update"] = "update_employeetype"
        if request.user.has_perm("staff.add_employee_type"):
            context["action"]["add"] = reverse('add_employeetype')
        if request.user.is_staff :
            context["action"]["admin"] = 'admin:staff_employee_type_change'
        
        return render(request=request,template_name=self.template_name,context=context)

class SettingList_GenericInfo(LoginRequiredMixin, TemplateView):
    template_name = 'settings/setting_table.html'
    model = GenericInfoType
    
    def get(self,request):
        context={
            'url':reverse_lazy("api:settinglist-genericinfotype"),
            'title':_('Generic Info Employee'),
            'columns':[
                {'name':_('name'),'item':'name',},
                {'name':_('Icon'),'item':'icon_val', 'formatter':'iconFormatter'},
            ], 
            'action':{
            },
            'options':{
            },         
        }
        if request.user.has_perm("staff.change_genericinfotype"):
            context["action"]["update"] = "update_genericinfotype"
        if request.user.has_perm("staff.add_genericinfotype"):
            context["action"]["add"] = reverse('add_genericinfotype')
        if request.user.is_staff :
            context["action"]["admin"] = 'admin:staff_genericinfotype_change'
        
        return render(request=request,template_name=self.template_name,context=context)
    
class SettingList_GenericInfoProject(LoginRequiredMixin, TemplateView):
    template_name = 'settings/setting_table.html'
    model = GenericInfoTypeProject
    
    def get(self,request):
        context={
            'url':reverse_lazy("api:settinglist-genericinfotypeproject"),
            'title':_('Generic Info Project'),
            'columns':[
                {'name':_('name'),'item':'name',},
                {'name':_('Icon'),'item':'icon_val', 'formatter':'iconFormatter'},
            ], 
            'action':{
            },
            'options':{
            },         
        }
        if request.user.has_perm("project.change_genericinfotypeproject"):
            context["action"]["update"] = "update_genericinfotypeproject"
        if request.user.has_perm("project.add_genericinfotypeproject"):
            context["action"]["add"] = reverse('add_genericinfotypeproject')
        if request.user.is_staff :
            context["action"]["admin"] = 'admin:project_genericinfotypeproject_change'
        
        return render(request=request,template_name=self.template_name,context=context)
    
    
    
class Subscription_List(LoginRequiredMixin, TemplateView):
    template_name = 'settings/setting_table.html'
    model = subscription
    
    def get(self,request):
        # print("[Subscription_List] - get")
        context={
            'url':reverse_lazy("api:subscription-current_user"),
            'title':_('Subscriptions'),
            'columns':[
                {'name':_('User'),'item':'user.username',},
                {'name':_('Type'),'item':'content_type.modelname',},
                {'name':_('Item'),'item':'object_name',},
            ], 
            'action':{
            },
            'options':{
            },         
        }
        if request.user.has_perm("common.delete_subscription"):
            context["action"]["delete"] = "delete_subscription"
        if request.user.is_staff :
            context["action"]["admin"] = 'admin:common_subscription_change'
        
        return render(request=request,template_name=self.template_name,context=context)