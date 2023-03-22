from django.shortcuts import render
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic.base import TemplateView
from django.utils.translation import gettext_lazy as _
from view_breadcrumbs import BaseBreadcrumbMixin

from .models import LMUserSetting

from fund.models import Cost_Type

class SettingsView(LoginRequiredMixin, BaseBreadcrumbMixin, TemplateView):
    template_name = 'settings/settings.html'
    home_label = '<i class="fas fa-bars"></i>'
    model = LMUserSetting
    crumbs = [("Settings","settings")]
    
class SettingList_cost_type(LoginRequiredMixin, TemplateView):
    template_name = 'settings/setting_table.html'
    model = Cost_Type
