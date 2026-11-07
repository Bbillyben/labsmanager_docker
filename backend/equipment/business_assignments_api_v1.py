"""Expense-centered business assignment operations for Equipment."""

from django.db import transaction
from django.shortcuts import get_object_or_404
from rest_framework import permissions, serializers, status
from rest_framework.response import Response
from rest_framework.views import APIView

from expense.models import Expense
from fund.financial_tools_api_v1 import visible_funds

from .api_v1 import validate_model, visible_equipment
from .expense_access import (assignment_capabilities, create_equipment_link,
                             require_assignment_capability, visible_linked_expenses)
from .models import EquipmentExpenseLink


def assignment_data(link):
    """Expose only public Equipment identity and the link's business nature."""
    return {"equipment": {"id": link.equipment_id, "name": link.equipment.name,
                           "internal_reference": link.equipment.internal_reference},
            "nature": link.nature}


class ExpenseBusinessAssignments(APIView):
    permission_classes = (permissions.IsAuthenticated,)

    def expense(self, *, lock=False):
        queryset = Expense.objects.filter(fund_item__in=visible_funds(self.request.user))
        queryset = visible_linked_expenses(self.request.user, queryset)
        if lock:
            queryset = queryset.select_for_update(of=("self",))
        return get_object_or_404(queryset, pk=self.kwargs["expense_id"])

    def link(self, expense):
        return get_object_or_404(EquipmentExpenseLink.objects.select_related("equipment"), expense=expense)

    def equipment(self, identifier):
        if not identifier:
            raise serializers.ValidationError({"equipment_id": "Choose an Equipment."})
        equipment_id = serializers.IntegerField(min_value=1).run_validation(identifier)
        return get_object_or_404(visible_equipment(self.request.user), pk=equipment_id)

    def nature(self, value):
        if value not in EquipmentExpenseLink.Nature.values:
            raise serializers.ValidationError({"nature": "Invalid nature."})
        return value

    def get(self, request, *args, **kwargs):
        expense = self.expense()
        require_assignment_capability(request.user, expense, "can_view")
        link = EquipmentExpenseLink.objects.filter(expense=expense).select_related("equipment").first()
        capabilities = assignment_capabilities(request.user, expense)
        return Response({"equipment": assignment_data(link) if link else None,
                         "capabilities": {"can_link": not link and capabilities["can_link"],
                                          "can_change": bool(link and capabilities["can_change"]),
                                          "can_unlink": bool(link and capabilities["can_unlink"])}})

    @transaction.atomic
    def post(self, request, *args, **kwargs):
        expense = self.expense(lock=True)
        require_assignment_capability(request.user, expense, "can_link")
        if set(request.data) != {"equipment_id", "nature"}:
            raise serializers.ValidationError({"detail": "Equipment and nature are required."})
        equipment = self.equipment(request.data["equipment_id"])
        link = create_equipment_link(equipment=equipment, expense=expense, nature=self.nature(request.data["nature"]))
        return Response(assignment_data(link), status=status.HTTP_201_CREATED)

    @transaction.atomic
    def patch(self, request, *args, **kwargs):
        expense = self.expense(lock=True)
        require_assignment_capability(request.user, expense, "can_change")
        if not request.data or set(request.data) - {"equipment_id", "nature"}:
            raise serializers.ValidationError({"detail": "Only Equipment and nature can change."})
        link = self.link(expense)
        updates = []
        if "equipment_id" in request.data:
            link.equipment = self.equipment(request.data["equipment_id"])
            updates.append("equipment")
        if "nature" in request.data:
            link.nature = self.nature(request.data["nature"])
            updates.append("nature")
        validate_model(link)
        link.save(update_fields=updates)
        return Response(assignment_data(link))

    @transaction.atomic
    def delete(self, request, *args, **kwargs):
        expense = self.expense(lock=True)
        require_assignment_capability(request.user, expense, "can_unlink")
        self.link(expense).delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
