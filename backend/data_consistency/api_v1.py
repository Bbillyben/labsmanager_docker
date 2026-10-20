"""Data Consistency review and exception endpoints."""

import logging

from django.db import IntegrityError, transaction
from django.http import Http404
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import generics, permissions, serializers
from rest_framework.exceptions import APIException, PermissionDenied, ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView

from expense.contract_hub_api_v1 import visible_contracts
from expense.models import Expense
from fund.financial_tools_api_v1 import visible_funds
from project.api_v1 import project_capabilities, project_child_capabilities
from labsmanager.pagination import LabPagination

from .models import DataConsistencyException
from .corrections import (can_correct_rule, correct_date_issue, correct_participant_issue,
                          correct_lifecycle_issue, correction_kind)
from .lifecycle import can_correct_item, visible_employees, visible_project_participants, visible_team_mates
from staff.permissions_v1 import employee_detail_capabilities
from .permissions import can_accept_exception, can_reopen_exception
from .service import (RULES, RULES_BY_KEY, PROJECT_LEADER_RULE_KEY, accepted_exceptions, accepted_issue,
                      active_issues, issue_identity, OBJECT_ID_FIELDS,
                      IDENTITY_PATHS, open_exceptions, summary, visible_milestones, visible_projects)


logger = logging.getLogger(__name__)


class StaleIssue(APIException):
    status_code = 409
    default_detail = "This consistency issue has changed or no longer exists."


class AcceptInput(serializers.Serializer):
    employee_id = serializers.IntegerField(min_value=1, required=False)
    project_id = serializers.IntegerField(min_value=1, required=False, allow_null=True)
    team_id = serializers.IntegerField(min_value=1, required=False)
    reason = serializers.CharField(required=False, allow_blank=True, max_length=1000)


class BatchIssueInput(serializers.Serializer):
    id = serializers.IntegerField(min_value=1)
    project_id = serializers.IntegerField(min_value=1, required=False, allow_null=True)
    employee_id = serializers.IntegerField(min_value=1, required=False)
    fund_id = serializers.IntegerField(min_value=1, required=False)
    team_id = serializers.IntegerField(min_value=1, required=False)


class BatchAcceptInput(serializers.Serializer):
    mode = serializers.ChoiceField(choices=("selected", "all"))
    issues = BatchIssueInput(many=True, required=False)
    excluded_ids = serializers.ListField(child=serializers.IntegerField(min_value=1), required=False)
    reason = serializers.CharField(required=False, allow_blank=True, max_length=1000)
    selected_count = serializers.IntegerField(min_value=0)

    def validate(self, attrs):
        if attrs["mode"] == "selected" and not attrs.get("issues"):
            raise ValidationError({"issues": "Select at least one issue."})
        if attrs["mode"] == "selected" and attrs.get("excluded_ids"):
            raise ValidationError({"excluded_ids": "Only global selection supports exclusions."})
        if attrs["mode"] == "all" and attrs.get("issues"):
            raise ValidationError({"issues": "Global selection does not accept issue IDs."})
        if len(attrs.get("issues", [])) > 1000 or len(attrs.get("excluded_ids", [])) > 1000:
            raise ValidationError("Too many issue IDs.")
        return attrs


def require_exception_permission(user, action):
    allowed = can_accept_exception(user) if action == "add" else can_reopen_exception(user)
    if not allowed:
        raise PermissionDenied()


def visible_items(user, rule):
    return {
        "contract": lambda: visible_contracts(user),
        "fund": lambda: visible_funds(user),
        "milestone": lambda: visible_milestones(user),
        "expense": lambda: Expense.objects.filter(fund_item__in=visible_funds(user)),
        "project": lambda: visible_projects(user),
        "employee": lambda: visible_employees(user),
        "teammate": lambda: visible_team_mates(user),
        "participant": lambda: visible_project_participants(user),
    }[rule.object_type]()


def accept_current_issue(user, rule, object_id, reason, expected=None):
    """Lock and re-evaluate an issue before creating its existing exception."""
    item = get_object_or_404(visible_items(user, rule).select_for_update(of=("self",)), pk=object_id)
    issue = rule.issues(user).filter(pk=item.pk).first()
    if issue is None:
        raise StaleIssue()
    identity = {"rule_key": rule.key, **issue_identity(rule, issue)}
    if expected and any(field in expected and expected[field] != value
                        for field, value in identity.items() if field != "rule_key"):
        raise StaleIssue()
    if open_exceptions().filter(**identity).exists():
        raise StaleIssue()
    exception = DataConsistencyException.objects.create(
        **identity, accepted_by=user, reason=reason,
    )
    return accepted_issue(exception, issue, rule)


class DataConsistencySummary(APIView):
    permission_classes = (permissions.IsAuthenticated,)
    http_method_names = ("get", "head", "options")

    def get(self, request):
        overview = summary(request.user)
        for row in overview["rules"]:
            rule = RULES_BY_KEY[row["rule_key"]]
            kind = correction_kind(rule)
            row["correction_action"] = (
                "add_participants" if kind == "participant" else
                "apply_correction" if kind == "lifecycle" else "extend_dates"
            ) if row["count"] and can_correct_rule(request.user, rule) else None
        return Response({**overview, "capabilities": {
            "can_accept": can_accept_exception(request.user),
            "can_reopen": can_reopen_exception(request.user),
        }})


class DataConsistencyIssues(generics.GenericAPIView):
    permission_classes = (permissions.IsAuthenticated,)
    pagination_class = LabPagination
    http_method_names = ("get", "head", "options")

    def serialize_item(self, user, rule, item):
        data = rule.serialize(item)
        kind = correction_kind(rule)
        if kind == "lifecycle":
            data["correction_action"] = "apply_correction" if can_correct_item(user, rule, item) else None
        elif kind == "participant" or rule.key == PROJECT_LEADER_RULE_KEY:
            project = item.fund.project if kind == "participant" else item
            visible = visible_projects(user).filter(pk=project.pk).exists()
            data["can_add_participant"] = bool(
                visible and project_child_capabilities(user, project, "participant")["can_add"]
            )
        elif kind == "project" and data.get("reason"):
            project = item.fund.project if rule.object_type == "contract" else item.project
            data["correction_action"] = (
                "extend_dates" if visible_projects(user).filter(pk=project.pk).exists()
                and project_capabilities(user, project)["can_change"] else None
            )
        if data.get("manual_url") and not employee_detail_capabilities(user, item)["can_change"]:
            data.pop("manual_url")
        return data

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
            return self.get_paginated_response([self.serialize_item(request.user, rule, item) for item in page])
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
        return Response(accept_current_issue(
            request.user, rule, object_id, data.validated_data.get("reason", ""), data.validated_data,
        ), status=201)


class DataConsistencyBatchAccept(APIView):
    permission_classes = (permissions.IsAuthenticated,)
    http_method_names = ("post", "options")

    def post(self, request, rule_key):
        require_exception_permission(request.user, "add")
        rule = RULES_BY_KEY.get(rule_key)
        if rule is None:
            raise ValidationError({"rule_key": "Unknown consistency rule."})
        data = BatchAcceptInput(data=request.data)
        data.is_valid(raise_exception=True)
        options = data.validated_data
        if options["mode"] == "all":
            excluded = set(options.get("excluded_ids", []))
            candidates = active_issues(request.user, rule).exclude(pk__in=excluded).values_list("pk", flat=True).iterator(chunk_size=200)
            expected_by_id = None
        else:
            selected = options["issues"]
            expected_by_id = {item["id"]: item for item in selected}
            if len(expected_by_id) != len(selected):
                raise ValidationError({"issues": "Duplicate issue ID."})
            candidates = expected_by_id.keys()
        processed = succeeded = skipped = failed = 0
        reason = options.get("reason", "")
        for object_id in candidates:
            processed += 1
            try:
                with transaction.atomic():
                    accept_current_issue(request.user, rule, object_id, reason,
                                         expected_by_id[object_id] if expected_by_id is not None else None)
                succeeded += 1
            except (StaleIssue, Http404):
                skipped += 1
            except IntegrityError:
                skipped += 1
            except Exception:
                logger.exception("Batch acceptance failed for rule %s and object %s", rule.key, object_id)
                failed += 1
        return Response({
            "initially_selected": options["selected_count"],
            "processed": processed, "succeeded": succeeded,
            "skipped": skipped, "failed": failed,
        })


class DataConsistencyCorrect(APIView):
    permission_classes = (permissions.IsAuthenticated,)
    http_method_names = ("post", "options")

    def post(self, request, rule_key, object_id):
        rule = RULES_BY_KEY.get(rule_key)
        if rule is None or correction_kind(rule) in (None, "participant"):
            raise ValidationError({"rule_key": "No automatic correction for this rule."})
        data = BatchIssueInput(data={**request.data, "id": object_id})
        data.is_valid(raise_exception=True)
        correct = correct_lifecycle_issue if correction_kind(rule) == "lifecycle" else correct_date_issue
        outcome = correct(request, rule, object_id, data.validated_data)
        if outcome == "ignored":
            raise PermissionDenied()
        if outcome == "resolved":
            raise StaleIssue()
        return Response({"status": outcome})


class DataConsistencyBatchCorrect(APIView):
    permission_classes = (permissions.IsAuthenticated,)
    http_method_names = ("post", "options")

    def post(self, request, rule_key):
        rule = RULES_BY_KEY.get(rule_key)
        if rule is None or correction_kind(rule) is None:
            raise ValidationError({"rule_key": "No automatic correction for this rule."})
        data = BatchAcceptInput(data=request.data)
        data.is_valid(raise_exception=True)
        options = data.validated_data
        if options["mode"] == "all":
            excluded = set(options.get("excluded_ids", []))
            # Freeze IDs before any mutation, while evaluating each item afresh later.
            if correction_kind(rule) == "lifecycle":
                selected = list(active_issues(request.user, rule).exclude(pk__in=excluded))
                expected_by_id = {item.pk: issue_identity(rule, item) for item in selected}
                candidates = list(expected_by_id)
            elif correction_kind(rule) == "participant":
                selected = list(active_issues(request.user, rule).exclude(pk__in=excluded)
                                .values("id", "employee_id", "fund_id", "fund__project_id"))
                expected_by_id = {item["id"]: {"project_id": item["fund__project_id"],
                                                "employee_id": item["employee_id"],
                                                "fund_id": item["fund_id"]} for item in selected}
                candidates = list(expected_by_id)
            else:
                candidates = list(active_issues(request.user, rule).exclude(pk__in=excluded).values_list("pk", flat=True))
                expected_by_id = None
        else:
            selected = options["issues"]
            expected_by_id = {item["id"]: item for item in selected}
            if len(expected_by_id) != len(selected):
                raise ValidationError({"issues": "Duplicate issue ID."})
            if correction_kind(rule) == "lifecycle":
                required = set(IDENTITY_PATHS[rule.object_type]) - {OBJECT_ID_FIELDS[rule.object_type]}
                if any(not required.issubset(item) for item in selected):
                    raise ValidationError({"issues": "Missing lifecycle issue identity."})
            candidates = list(expected_by_id)
        counts = {"selected": len(candidates), "corrected": 0, "already_resolved": 0,
                  "ignored": 0, "failed": 0}
        correct = (correct_participant_issue if correction_kind(rule) == "participant" else
                   correct_lifecycle_issue if correction_kind(rule) == "lifecycle" else correct_date_issue)
        for object_id in candidates:
            try:
                outcome = correct(request, rule, object_id,
                                  expected_by_id[object_id] if expected_by_id is not None else None)
                counts[{"corrected": "corrected", "resolved": "already_resolved", "ignored": "ignored"}[outcome]] += 1
            except (Http404, PermissionDenied):
                counts["ignored"] += 1
            except Exception:
                logger.exception("Batch correction failed for rule %s and object %s", rule.key, object_id)
                counts["failed"] += 1
        return Response(counts)


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
