"""Simple administrative access to the Equipment catalogue and its history."""

from django.contrib import admin
from django import forms

from expense.api_v1 import expense_capabilities
from expense.models import Expense
from fund.financial_tools_api_v1 import visible_funds

from .api_v1 import visible_equipment

from .models import (
    Equipment,
    EquipmentExpenseLink,
    EquipmentCategory,
    EquipmentGenericInfo,
    EquipmentGenericInfoType,
    EquipmentInstitutionInventory,
    EquipmentResponsibility,
    EquipmentMaintenance,
)


@admin.register(Equipment)
class EquipmentAdmin(admin.ModelAdmin):
    list_display = ("name", "internal_reference", "category", "status")
    list_filter = ("category", "status")
    search_fields = ("name", "internal_reference")

    def get_readonly_fields(self, request, obj=None):
        return ("internal_reference",) if obj else ()


@admin.register(EquipmentCategory)
class EquipmentCategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "is_active")
    list_filter = ("is_active",)
    search_fields = ("name",)


@admin.register(EquipmentGenericInfoType)
class EquipmentGenericInfoTypeAdmin(admin.ModelAdmin):
    list_display = ("name", "icon")
    search_fields = ("name",)


@admin.register(EquipmentGenericInfo)
class EquipmentGenericInfoAdmin(admin.ModelAdmin):
    list_display = ("equipment", "info", "value")
    search_fields = ("equipment__name", "equipment__internal_reference", "info__name", "value")


@admin.register(EquipmentResponsibility)
class EquipmentResponsibilityAdmin(admin.ModelAdmin):
    list_display = ("equipment", "employee", "start_date", "end_date")
    search_fields = ("equipment__name", "equipment__internal_reference")


@admin.register(EquipmentInstitutionInventory)
class EquipmentInstitutionInventoryAdmin(admin.ModelAdmin):
    list_display = ("equipment", "institution", "inventory_number", "status", "start_date", "end_date")
    list_filter = ("status", "institution")
    search_fields = ("equipment__name", "equipment__internal_reference", "inventory_number")


@admin.register(EquipmentExpenseLink)
class EquipmentExpenseLinkAdmin(admin.ModelAdmin):
    list_display = ("equipment", "expense", "nature")
    list_filter = ("nature",)
    search_fields = ("equipment__name", "equipment__internal_reference", "expense__expense_id", "expense__desc")
    autocomplete_fields = ()

    def has_change_permission(self, request, obj=None):
        return (super().has_change_permission(request, obj) and
                (obj is None or expense_capabilities(request.user, obj.expense)["can_change"]))

    def has_delete_permission(self, request, obj=None):
        return (super().has_delete_permission(request, obj) and
                (obj is None or expense_capabilities(request.user, obj.expense)["can_change"]))

    def get_queryset(self, request):
        return (super().get_queryset(request)
                .filter(equipment__in=visible_equipment(request.user), expense__fund_item__in=visible_funds(request.user)))

    def get_readonly_fields(self, request, obj=None):
        return ("equipment", "expense") if obj else ()

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == "equipment":
            kwargs["queryset"] = visible_equipment(request.user)
        elif db_field.name == "expense":
            kwargs["queryset"] = Expense.objects.filter(
                fund_item__in=visible_funds(request.user), equipment_link__isnull=True)
        return super().formfield_for_foreignkey(db_field, request, **kwargs)

    def get_form(self, request, obj=None, **kwargs):
        base_form = super().get_form(request, obj, **kwargs)

        class LinkForm(base_form):
            def clean(self):
                data = super().clean()
                if obj is None and data.get("expense") and not expense_capabilities(request.user, data["expense"])["can_change"]:
                    raise forms.ValidationError("You cannot link this financial Expense.")
                return data

        return LinkForm


@admin.register(EquipmentMaintenance)
class EquipmentMaintenanceAdmin(admin.ModelAdmin):
    list_display = ("title", "equipment", "maintenance_type", "status", "scheduled_date", "performed_date")
    list_filter = ("maintenance_type", "status", "scheduled_date")
    search_fields = ("title", "equipment__name", "equipment__internal_reference")

    def get_queryset(self, request):
        return super().get_queryset(request).filter(equipment__in=visible_equipment(request.user))

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == "equipment":
            kwargs["queryset"] = visible_equipment(request.user)
        elif db_field.name == "expense_link":
            kwargs["queryset"] = EquipmentExpenseLink.objects.filter(
                equipment__in=visible_equipment(request.user), expense__fund_item__in=visible_funds(request.user))
        return super().formfield_for_foreignkey(db_field, request, **kwargs)
