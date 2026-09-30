"""Project-scoped Calendar events, participants and contextual Leave creation."""

from datetime import date

from django.shortcuts import get_object_or_404
from django.http import Http404
from rest_framework import permissions
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView

from common.calendar import CalendarContext, CalendarService, CalendarType
from leave.calendar import produce_leave_calendar_events
from leave.models import Leave
from project.models import Participant, Project
from staff.permissions_v1 import leave_capabilities
from staff.serializers_v1 import EmployeeLeaveV1Serializer, EmployeeLeaveWriteV1Serializer


class ProjectCalendarBaseV1View(APIView):
    permission_classes = (permissions.IsAuthenticated,)

    def project(self):
        visible = Project.get_instances_for_user("view", self.request.user, Project.objects.all())
        return get_object_or_404(visible, pk=self.kwargs["project_id"])

    def context(self, *, bounded=False):
        project = self.project()
        start = end = None
        if bounded:
            try:
                start = date.fromisoformat(self.request.query_params.get("from", ""))
                end = date.fromisoformat(self.request.query_params.get("to", ""))
            except ValueError as exc:
                raise ValidationError({"from": "Expected ISO from and to dates."}) from exc
            if start > end:
                raise ValidationError({"to": "Must be on or after from."})
        return CalendarContext(
            calendar_type=CalendarType.PROJECT,
            user=self.request.user,
            start=start,
            end=end,
            project_id=project.pk,
            filters=self.request.query_params,
        )


class ProjectCalendarV1View(ProjectCalendarBaseV1View):
    def get(self, request, *args, **kwargs):
        context = self.context(bounded=True)
        service = CalendarService()
        events = service.get_events(context, produce_leave_calendar_events(context, service))
        return Response([event.as_dict() for event in events])


class ProjectCalendarFiltersV1View(ProjectCalendarBaseV1View):
    def get(self, request, *args, **kwargs):
        return Response([item.as_dict() for item in CalendarService().get_filters(self.context())])


class ProjectCalendarParticipantsV1View(ProjectCalendarBaseV1View):
    def get(self, request, *args, **kwargs):
        project = self.project()
        employees = (
            Participant.objects.filter(project=project)
            .select_related("employee")
            .order_by("employee__last_name", "employee__first_name", "employee_id")
        )
        seen = set()
        resources = []
        for relation in employees:
            employee = relation.employee
            if employee.pk in seen:
                continue
            seen.add(employee.pk)
            resources.append({
                "id": employee.pk,
                "title": str(employee),
                "capabilities": leave_capabilities(request.user, employee),
            })
        return Response(resources)


class ProjectCalendarLeaveCreateV1View(ProjectCalendarBaseV1View):
    """Use the Employee Leave write contract within an authorized Project scope."""

    def post(self, request, *args, **kwargs):
        project = self.project()
        try:
            employee_id = int(request.data.get("employee_id"))
        except (TypeError, ValueError) as exc:
            raise ValidationError({"employee_id": "Expected a participant Employee id."}) from exc
        participant = Participant.objects.filter(project=project, employee_id=employee_id).select_related("employee").first()
        if participant is None:
            raise Http404
        employee = participant.employee
        if not leave_capabilities(request.user, employee)["can_add"]:
            raise PermissionDenied()
        write_data = {key: value for key, value in request.data.items() if key != "employee_id"}
        serializer = EmployeeLeaveWriteV1Serializer(data=write_data)
        serializer.is_valid(raise_exception=True)
        leave = serializer.save(employee=employee)
        return Response(EmployeeLeaveV1Serializer(leave).data, status=201)


class ProjectCalendarLeaveDetailV1View(ProjectCalendarBaseV1View):
    """Mutate a participant Leave without requiring Employee-page visibility."""

    def leave(self):
        project = self.project()
        employees = Participant.objects.filter(project=project).values("employee_id")
        return get_object_or_404(
            Leave.objects.select_related("type").filter(employee_id__in=employees),
            pk=self.kwargs["leave_id"],
        )

    def patch(self, request, *args, **kwargs):
        leave = self.leave()
        if not leave_capabilities(request.user, leave.employee)["can_change"]:
            raise PermissionDenied()
        serializer = EmployeeLeaveWriteV1Serializer(leave, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        return Response(EmployeeLeaveV1Serializer(serializer.save()).data)

    def delete(self, request, *args, **kwargs):
        leave = self.leave()
        if not leave_capabilities(request.user, leave.employee)["can_delete"]:
            raise PermissionDenied()
        leave.delete()
        return Response(status=204)
