"""Read-only Data Consistency endpoints."""

from django.db import transaction
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import generics, permissions, serializers
from rest_framework.exceptions import APIException, PermissionDenied, ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView

from expense.contract_hub_api_v1 import visible_contracts
from expense.models import Expense
from fund.financial_tools_api_v1 import visible_funds
from labsmanager.pagination import LabPagination

from .models import DataConsistencyException
from .permissions import can_accept_exception, can_reopen_exception
from .service import (RULES, RULES_BY_KEY, accepted_exceptions, accepted_issue,
                      active_issues, issue_identity, OBJECT_ID_FIELDS,
                      open_exceptions, summary, visible_milestones, visible_projects)


class StaleIssue(APIException):
    status_code = 409
    default_detail = "This consistency issue has changed or no longer exists."


class AcceptInput(serializers.Serializer):
    employee_id = serializers.IntegerField(min_value=1, required=False)
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
        # Each rule owns a database queryset; pagination never materializes
        # all issues. The first rule remains the default for older clients.
        rule = RULES_BY_KEY[rule_key] if rule_key else RULES[0]
        if status == "active":
            page = self.paginate_queryset(active_issues(request.user, rule))
            return self.get_paginated_response([rule.serialize(item) for item in page])
        page = self.paginate_queryset(accepted_exceptions(request.user, rule))
        id_field = OBJECT_ID_FIELDS[rule.object_type]
        items = {item.pk: item for item in rule.issues(request.user).filter(
            pk__in=[getattr(exception, id_field) for exception in page]
        )}
        return self.get_paginated_response([
            accepted_issue(exception, items[getattr(exception, id_field)], rule) for exception in page
        ])


class DataConsistencyAccept(APIView):
    permission_classes = (permissions.IsAuthenticated,)
    http_method_names = ("post", "options")

    @transaction.atomic
    def post(self, request, rule_key, object_id):
        require_exception_permission(request.user, "add")
        rule = RULES_BY_KEY.get(rule_key)
        if rule is None:
            raise ValidationError({"rule_key": "Unknown consistency rule."})
        data = AcceptInput(data=request.data)
        data.is_valid(raise_exception=True)
        visible = {
            "contract": lambda: visible_contracts(request.user),
            "fund": lambda: visible_funds(request.user),
            "milestone": lambda: visible_milestones(request.user),
            "expense": lambda: Expense.objects.filter(fund_item__in=visible_funds(request.user)),
            "project": lambda: visible_projects(request.user),
        }[rule.object_type]()
        item = get_object_or_404(visible.select_for_update(of=("self",)), pk=object_id)
        issue = rule.issues(request.user).filter(pk=item.pk).first()
        if issue is None:
            raise StaleIssue()
        identity = {"rule_key": rule.key, **issue_identity(rule, issue)}
        if (identity["project_id"] != data.validated_data["project_id"] or
                (rule.object_type == "contract" and identity["employee_id"] != data.validated_data.get("employee_id"))):
            raise StaleIssue()
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
