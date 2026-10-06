"""Permission-scoped v1 entry point to the existing report renderers."""

from datetime import date

from django.core.exceptions import PermissionDenied as DjangoPermissionDenied
from django.http import Http404
from django.shortcuts import get_object_or_404
from rest_framework import permissions, serializers
from rest_framework.exceptions import PermissionDenied
from rest_framework.response import Response
from rest_framework.views import APIView

from project.models import Project
from staff.models import Employee

from .models import (
    EmployeePDFReport,
    EmployeeWordReport,
    ProjectPDFReport,
    ProjectWordReport,
)


REPORTS = {
    ("project", "word"): (Project, ProjectWordReport, "reports.view_projectwordreport"),
    ("project", "pdf"): (Project, ProjectPDFReport, "reports.view_projectpdfreport"),
    ("employee", "word"): (Employee, EmployeeWordReport, "reports.view_employeewordreport"),
    ("employee", "pdf"): (Employee, EmployeePDFReport, "reports.view_employeepdfreport"),
}


def report_capabilities(user, entity, instance):
    """Match legacy's global-or-object permission check for each format."""
    return {
        f"can_export_{format_name}": bool(
            user.has_perm(REPORTS[(entity, format_name)][2])
            or user.has_perm(REPORTS[(entity, format_name)][2], instance)
        )
        for format_name in ("word", "pdf")
    }


def scoped_report(user, entity, pk, format_name):
    """Resolve report access for both v1 and the existing direct legacy URLs."""
    config = REPORTS.get((entity, format_name))
    if config is None:
        raise Http404
    model, report_model, permission = config
    visible = model.get_instances_for_user("view", user, model.objects.all())
    instance = get_object_or_404(visible, pk=pk)
    if not (user.has_perm(permission) or user.has_perm(permission, instance)):
        raise DjangoPermissionDenied
    return report_model, instance


def validate_legacy_employee_dates(request):
    values = []
    for field in ("start_date", "end_date"):
        raw = request.GET.get(field)
        if not raw:
            values.append(None)
            continue
        try:
            values.append(date.fromisoformat(raw))
        except ValueError:
            return False
    return not (values[0] and values[1] and values[0] > values[1])


class ReportExportWriteSerializer(serializers.Serializer):
    template_id = serializers.IntegerField(min_value=1)
    start_date = serializers.DateField(required=False, allow_null=True)
    end_date = serializers.DateField(required=False, allow_null=True)

    def validate(self, attrs):
        if self.context["entity"] == "project" and ("start_date" in attrs or "end_date" in attrs):
            raise serializers.ValidationError("Project reports do not accept dates.")
        start, end = attrs.get("start_date"), attrs.get("end_date")
        if start and end and start > end:
            raise serializers.ValidationError({"end_date": "End date must be on or after start date."})
        return attrs


class ReportExportV1View(APIView):
    permission_classes = (permissions.IsAuthenticated,)

    def context(self, request, entity, pk, format_name):
        try:
            return scoped_report(request.user, entity, pk, format_name)
        except DjangoPermissionDenied as error:
            raise PermissionDenied() from error

    def get(self, request, entity, pk, format_name):
        report_model, _ = self.context(request, entity, pk, format_name)
        return Response({"templates": list(report_model.objects.all().order_by("pk").values("id", "name"))})

    def post(self, request, entity, pk, format_name):
        report_model, instance = self.context(request, entity, pk, format_name)
        serializer = ReportExportWriteSerializer(data=request.data, context={"entity": entity})
        serializer.is_valid(raise_exception=True)
        report = get_object_or_404(report_model.objects.all(), pk=serializer.validated_data["template_id"])
        raw_request = request._request
        dates = raw_request.GET.copy()
        if entity == "employee":
            for field in ("start_date", "end_date"):
                value = serializer.validated_data.get(field)
                if value:
                    dates[field] = value.isoformat()
                else:
                    dates.pop(field, None)
        raw_request.GET = dates
        return report.render(raw_request, {"pk": instance.pk})
