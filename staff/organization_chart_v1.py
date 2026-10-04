"""Visible Employee hierarchy as a flat directed graph for the React chart."""

from collections import defaultdict, deque

from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from settings.models import LMUserSetting

from .models import Employee, Employee_Status, Employee_Superior


def cyclic_employee_ids(employee_ids, relationships):
    """Return the IDs left in a graph after topological traversal."""
    indegree = {employee_id: 0 for employee_id in employee_ids}
    children = defaultdict(list)
    for superior_id, employee_id in relationships:
        children[superior_id].append(employee_id)
        indegree[employee_id] += 1
    queue = deque(employee_id for employee_id, degree in indegree.items() if degree == 0)
    while queue:
        for child_id in children[queue.popleft()]:
            indegree[child_id] -= 1
            if indegree[child_id] == 0:
                queue.append(child_id)
    return sorted(employee_id for employee_id, degree in indegree.items() if degree)


class OrganizationChartV1View(APIView):
    permission_classes = (permissions.IsAuthenticated,)

    def get(self, request):
        # The historical key is inverted in name only: True means current only.
        current_only = LMUserSetting.get_setting("SHOW_PAST_ORG", user=request.user)
        visible = Employee.get_instances_for_user("view", request.user, Employee.objects.all())
        if current_only:
            visible = visible.filter(is_active=True)
        employees = list(visible.order_by("pk").values("id", "first_name", "last_name", "is_active"))
        employee_ids = {employee["id"] for employee in employees}

        relations = Employee_Superior.current if current_only else Employee_Superior.objects
        pairs = set(relations.filter(
            superior_id__in=employee_ids, employee_id__in=employee_ids
        ).values_list("superior_id", "employee_id"))
        cycles = cyclic_employee_ids(employee_ids, pairs)
        if cycles:
            return Response({"detail": "hierarchy_cycle", "employee_ids": cycles}, status=status.HTTP_409_CONFLICT)

        statuses = Employee_Status.current if current_only else Employee_Status.objects
        status_by_employee = defaultdict(list)
        for employee_id, shortname, name in statuses.filter(
            employee_id__in=employee_ids
        ).values_list("employee_id", "type__shortname", "type__name"):
            status_by_employee[employee_id].append({"code": shortname, "name": name})

        return Response({
            "show_current_only": current_only,
            "employees": [
                {
                    "id": employee["id"],
                    "name": f'{employee["first_name"]} {employee["last_name"]}',
                    "is_active": employee["is_active"],
                    "statuses": status_by_employee[employee["id"]],
                    "can_view": True,
                }
                for employee in employees
            ],
            "relationships": [
                {"superior_id": superior_id, "employee_id": employee_id}
                for superior_id, employee_id in sorted(pairs)
            ],
        })

    def patch(self, request):
        value = request.data.get("show_current_only")
        if not isinstance(value, bool):
            return Response({"show_current_only": ["Expected a boolean."]}, status=status.HTTP_400_BAD_REQUEST)
        LMUserSetting.set_setting("SHOW_PAST_ORG", value, change_user=None, user=request.user)
        return Response({"show_current_only": value})
