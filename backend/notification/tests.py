from datetime import date, timedelta
from types import SimpleNamespace
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase

from dashboard.business_sources import planning
from endpoints.models import Milestones
from notification.utils import check_stale_milestones
from project.models import Project
from settings.models import LMUserSetting
from staff.models import Employee


class MilestoneUpcomingThresholdTests(TestCase):
    def test_custom_day_threshold_is_shared_with_dashboard_and_notifications(self):
        today = date(2026, 1, 31)
        user = get_user_model().objects.create_user(username="milestone-threshold")
        employee = Employee.objects.create(first_name="Threshold", last_name="Reader", user=user)
        project = Project.objects.create(name="Threshold project")
        LMUserSetting.objects.create(user=user, key="DASHBOARD_MILESTONES_STALE_TO_DAYS", value="30")
        LMUserSetting.objects.create(user=user, key="NOTIFICATION_ENDPOINTS_MILESTONES", value=True)

        milestones = {}
        for label, offset in (("overdue", -1), ("before", 29), ("at", 30), ("after", 31)):
            milestone = Milestones.objects.create(name=label, project=project, end_date=today + timedelta(days=offset))
            milestone.employee.add(employee)
            milestones[label] = milestone

        context = SimpleNamespace(user=user, scope="personal")
        with patch("dashboard.business_sources.timezone.localdate", return_value=today), patch(
            "dashboard.business_sources.planning_queryset", return_value=Milestones.objects.filter(project=project)
        ):
            dashboard = planning(context, {}, tasks=False)["__renderers__"]["deadline-list"]
        states = {item["label"]: item["state"] for item in dashboard["items"]}
        self.assertEqual(dashboard["summary"]["due_soon_count"], 2)
        self.assertEqual(dashboard["summary"]["overdue_count"], 1)
        self.assertEqual(states, {"overdue": "overdue", "before": "due_soon", "at": "due_soon", "after": "upcoming"})

        with patch("notification.utils.date") as current_date, patch("notification.utils._add_notification", return_value=1) as add:
            current_date.today.return_value = today
            self.assertEqual(check_stale_milestones(), 2)
        self.assertEqual({call.args[1].pk for call in add.call_args_list}, {milestones["before"].pk, milestones["at"].pk})
