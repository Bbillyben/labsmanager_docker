from django.utils.translation import gettext_lazy as _
from django.shortcuts import render, get_object_or_404
from django.views.generic.base import TemplateView
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from view_breadcrumbs import BaseBreadcrumbMixin


from . import mixin

class ImportViewBase(LoginRequiredMixin, PermissionRequiredMixin, BaseBreadcrumbMixin, TemplateView):
    permission_required='common.import'
    template_name = 'import/import_base.html'
    crumbs = [(_("import"),"import")]


from fund.resources import FundItemAdminResource
from fund.models import Fund_Item
from expense.resources import ExpensePointResource
from expense.models import Expense_point
class FundItemImportView(LoginRequiredMixin, PermissionRequiredMixin, mixin.ImportViewMixin):
    permission_required='common.import'
    # resource_class = FundItemAdminResource
    resource_classes =[FundItemAdminResource, ExpensePointResource]
    model = Fund_Item
    
class FundItemImportViewConfirmImportView(LoginRequiredMixin, PermissionRequiredMixin, mixin.ConfirmImportViewMixin):
        permission_required='common.import'
        # resource_class = FundItemAdminResource
        resource_classes =[FundItemAdminResource, ExpensePointResource]
        model = Fund_Item