"""Read-only Data Consistency endpoints."""

from django.db import transaction
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import generics, permissions, serializers
from rest_framework.exceptions import APIException, PermissionDenied, ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView

from expense.contract_hub_api_v1 import visible_contracts
from labsmanager.pagination import LabPagination

from .models import DataConsistencyException
from .permissions import can_accept_exception, can_reopen_exception
from .service import (RULES, RULES_BY_KEY, accepted_exceptions, accepted_issue,
                      active_issues, open_exceptions, summary)


class StaleIssue(APIException):
    status_code = 409
    default_detail = "This consistency issue has changed or no longer exists."


class AcceptInput(serializers.Serializer):
    employee_id = serializers.IntegerField(min_value=1)
    project_id = serializers.IntegerField(min_value=1)
    reason = serializers.CharField(required=False, allow_blank=True, max_length=1000)


def require_exception_permission(user, action):
    allowed = can_accept_exception(user) if action == "add" else can_reopen_exception(user)
    if not allowed:
        raise PermissionDenied()


class DataConsistencySummary(APIView):
    permission_classes = (permissions.IsAuthenticated,)
    http_method_names = ("get", "head", "options")

    def get(self, request):
        return Response({**summary(request.user), "capabilities": {
            "can_accept": can_accept_exception(request.user),
            "can_reopen": can_reopen_exception(request.user),
        }})


class DataConsistencyIssues(generics.GenericAPIView):
    permission_classes = (permissions.IsAuthenticated,)
    pagination_class = LabPagination
    http_method_names = ("get", "head", "options")

    def get(self, request):
        status = request.query_params.get("status", "active")
        if status not in ("active", "accepted"):
            raise ValidationError({"status": "Expected active or accepted."})
        rule_key = request.query_params.get("rule_key")
        if rule_key and rule_key not in RULES_BY_KEY:
            raise ValidationError({"rule_key": "Unknown consistency rule."})
        if not rule_key and len(RULES) != 1:
            raise ValidationError({"rule_key": "Select a consistency rule."})
        # Each rule owns a database queryset; pagination never materializes
        # all issues. With more rules, callers select a rule from the summary.
        rule = RULES_BY_KEY[rule_key] if rule_key else RULES[0]
        if status == "active":
            page = self.paginate_queryset(active_issues(request.user, rule))
            return self.get_paginated_response([rule.serialize(item) for item in page])
        page = self.paginate_queryset(accepted_exceptions(request.user, rule))
        contracts = {item.pk: item for item in rule.issues(request.user).filter(
            pk__in=[item.contract_id for item in page]
        )}
        return self.get_paginated_response([
            accepted_issue(item, contracts[item.contract_id], rule) for item in page
        ])


class DataConsistencyAccept(APIView):
    permission_classes = (permissions.IsAuthenticated,)
    http_method_names = ("post", "options")

    @transaction.atomic
    def post(self, request, rule_key, contract_id):
        require_exception_permission(request.user, "add")
        rule = RULES_BY_KEY.get(rule_key)
        if rule is None:
            raise ValidationError({"rule_key": "Unknown consistency rule."})
        data = AcceptInput(data=request.data)
        data.is_valid(raise_exception=True)
        contract = get_object_or_404(visible_contracts(request.user).select_for_update(of=("self",)), pk=contract_id)
        issue = rule.issues(request.user).filter(pk=contract.pk).first()
        if (issue is None or issue.employee_id != data.validated_data["employee_id"]
                or issue.fund.project_id != data.validated_data["project_id"]):
            raise StaleIssue()
        identity = {"rule_key": rule.key, "contract_id": contract.pk,
                    "employee_id": issue.employee_id, "project_id": issue.fund.project_id}
        if open_exceptions().filter(**identity).exists():
            raise StaleIssue()
        exception = DataConsistencyException.objects.create(
            **identity, accepted_by=request.user, reason=data.validated_data.get("reason", ""),
        )
        return Response(accepted_issue(exception, issue, rule), status=201)


class DataConsistencyReopen(APIView):
    permission_classes = (permissions.IsAuthenticated,)
    http_method_names = ("post", "options")

    @transaction.atomic
    def post(self, request, exception_id):
        require_exception_permission(request.user, "change")
        exception = get_object_or_404(open_exceptions().select_for_update(), pk=exception_id)
        rule = RULES_BY_KEY.get(exception.rule_key)
        if rule is None or not accepted_exceptions(request.user, rule).filter(pk=exception.pk).exists():
            raise StaleIssue()
        exception.closed_at = timezone.now()
        exception.closed_reason = "reopened"
        exception.save(update_fields=("closed_at", "closed_reason"))
        return Response({"id": exception.pk, "status": "reopened"})
