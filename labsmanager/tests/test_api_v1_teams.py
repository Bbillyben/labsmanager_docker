from datetime import date
from decimal import Decimal
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from rest_framework.test import APITestCase

from common.calendar import LabsManagerCalendarEvent
from fund.models import Budget, Cost_Type, Fund, Fund_Institution
from leave.models import Leave, Leave_Type
from project.models import Institution, Participant, Project
from staff.models import Employee, Team, TeamMate


class TeamV1Tests(APITestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username="team-reader")
        self.other_user = get_user_model().objects.create_user(username="team-leader")
        self.reader = Employee.objects.create(first_name="Reader", last_name="Person", user=self.user)
        self.leader = Employee.objects.create(first_name="Team", last_name="Leader", user=self.other_user)
        self.mate = Employee.objects.create(first_name="Team", last_name="Mate")
        self.outsider = Employee.objects.create(first_name="Outside", last_name="Person")
        self.team = Team.objects.create(name="Alpha", leader=self.leader)
        self.relation = TeamMate.objects.create(team=self.team, employee=self.reader)
        TeamMate.objects.create(team=self.team, employee=self.mate)
        self.hidden_team = Team.objects.create(name="Hidden", leader=self.outsider)
        self.client.force_login(self.user)

    def grant(self, app, code):
        self.user.user_permissions.add(Permission.objects.get(content_type__app_label=app, codename=code))
        self.user = get_user_model().objects.get(pk=self.user.pk)
        self.client.force_login(self.user)

    def url(self, suffix=""):
        return f"/api/v1/teams/{self.team.pk}/{suffix}"

    def test_list_filters_order_pagination_and_export_share_scope(self):
        extra = Team.objects.create(name="Beta", leader=self.reader)
        TeamMate.objects.create(team=extra, employee=self.mate)
        list_url = "/api/v1/teams/"
        response = self.client.get(list_url, {"leader": self.leader.pk, "mate": self.reader.pk, "name": "alp"})
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual([item["name"] for item in response.data["results"]], ["Alpha"])
        self.assertEqual(self.client.get(list_url, {"mate": self.leader.pk}).data["count"], 0)
        self.assertEqual(self.client.get(list_url, {"leader": "invalid"}).status_code, 400)
        self.assertEqual(self.client.get(list_url, {"ordering": "-name", "limit": 1}).data["results"][0]["name"], "Beta")
        self.assertEqual(self.client.get(list_url, {"ordering": "-name", "limit": 1, "offset": 1}).data["results"][0]["name"], "Alpha")
        for format_name in ("csv", "tsv", "xls", "xlsx"):
            export = self.client.get("/api/v1/teams/export/", {"name": "alp", "format": format_name, "limit": 1, "offset": 1})
            self.assertEqual(export.status_code, 200, format_name)
            self.assertIn(f".{format_name}", export["Content-Disposition"])
            if format_name in ("csv", "tsv"):
                content = export.content.decode()
                self.assertIn("Alpha", content)
                self.assertNotIn("Hidden", content)

    def test_detail_and_composition_use_existing_team_change_rule(self):
        detail = self.client.get(self.url())
        self.assertEqual(detail.status_code, 200)
        self.assertFalse(detail.data["capabilities"]["can_change"])
        self.assertEqual(len(detail.data["mates"]), 2)
        self.assertEqual(self.client.get(f"/api/v1/teams/{self.hidden_team.pk}/").status_code, 404)
        self.assertEqual(self.client.patch(self.url(), {"leader_id": self.mate.pk}, format="json").status_code, 403)
        self.assertEqual(self.client.post(self.url("mates/"), {"employee_id": self.outsider.pk}, format="json").status_code, 403)
        self.client.force_login(self.other_user)
        self.assertTrue(self.client.get(self.url()).data["capabilities"]["can_manage_composition"])
        self.assertEqual(self.client.patch(self.url(), {"leader_id": self.mate.pk}, format="json").status_code, 400)
        self.assertEqual(self.client.delete(self.url(f"mates/{self.relation.pk}/")).status_code, 204)
        created = self.client.post(self.url("mates/"), {"employee_id": self.outsider.pk}, format="json")
        self.assertEqual(created.status_code, 201, created.data)
        self.assertEqual(self.client.post(self.url("mates/"), {"employee_id": self.outsider.pk}, format="json").status_code, 400)
        changed = self.client.patch(self.url(), {"leader_id": self.reader.pk}, format="json")
        self.assertEqual(changed.status_code, 200)
        self.assertFalse(changed.data["capabilities"]["can_view"])

    def test_create_team_uses_add_permission_and_historical_leader_scope(self):
        payload = {"name": "New Team", "leader_id": self.reader.pk}
        self.assertFalse(self.client.get("/api/v1/teams/").data["capabilities"]["can_add"])
        self.assertEqual(self.client.post("/api/v1/teams/", payload, format="json").status_code, 403)
        self.grant("staff", "add_team")
        capabilities = self.client.get("/api/v1/teams/").data["capabilities"]
        self.assertTrue(capabilities["can_add"])
        self.assertFalse(capabilities["can_choose_leader"])
        self.assertEqual(capabilities["default_leader"]["id"], self.reader.pk)
        self.assertEqual(self.client.post("/api/v1/teams/", {**payload, "leader_id": self.outsider.pk}, format="json").status_code, 403)
        created = self.client.post("/api/v1/teams/", payload, format="json")
        self.assertEqual(created.status_code, 201, created.data)
        self.assertEqual(created.data["name"], "New Team")
        self.assertEqual(self.client.post("/api/v1/teams/", payload, format="json").status_code, 400)
        self.grant("staff", "change_team")
        self.assertTrue(self.client.get("/api/v1/teams/").data["capabilities"]["can_choose_leader"])
        self.assertEqual(self.client.post("/api/v1/teams/", {"name": "Another Team", "leader_id": self.outsider.pk}, format="json").status_code, 201)

    def test_mate_dates_status_edit_and_permissions(self):
        url = self.url(f"mates/{self.relation.pk}/")
        self.assertEqual(self.client.patch(url, {"start_date": "2020-01-01"}, format="json").status_code, 403)
        detail = self.client.get(self.url()).data
        self.assertIn("is_active", detail["mates"][0])
        self.assertFalse(detail["mates"][0]["capabilities"]["can_change"])
        self.client.force_login(self.other_user)
        changed = self.client.patch(url, {"start_date": "2020-01-01", "end_date": "2020-12-31"}, format="json")
        self.assertEqual(changed.status_code, 200, changed.data)
        self.assertFalse(changed.data["is_active"])
        self.assertEqual(next(mate for mate in self.client.get(self.url()).data["mates"] if mate["id"] == self.relation.pk)["start_date"], date(2020, 1, 1))
        self.assertEqual(self.client.patch(url, {"end_date": "2019-01-01"}, format="json").status_code, 400)
        self.assertEqual(self.client.patch(url, {"employee_id": self.mate.pk}, format="json").status_code, 400)
        changed = self.client.patch(url, {"employee_id": self.outsider.pk, "end_date": None}, format="json")
        self.assertEqual(changed.status_code, 200, changed.data)
        self.assertEqual(changed.data["employee_id"], self.outsider.pk)
        self.assertTrue(changed.data["is_active"])
        self.assertEqual(self.client.patch(self.url(), {"name": "Renamed", "leader_id": self.leader.pk}, format="json").status_code, 200)

    @patch("common.calendar.service.CalendarService.get_plugin_events")
    def test_calendar_members_plugins_and_leave_permissions(self, plugin_events):
        kind = Leave_Type.objects.create(short_name="CP", name="Leave", color="#336699")
        leave = Leave.objects.create(employee=self.mate, type=kind, start_date=date(2026, 9, 10), end_date=date(2026, 9, 12))
        Leave.objects.create(employee=self.outsider, type=kind, start_date=date(2026, 9, 10), end_date=date(2026, 9, 12))
        plugin_events.return_value = [LabsManagerCalendarEvent(id="plugin:1", title="Holiday", start=date(2026, 9, 11), source="plugin")]
        response = self.client.get(self.url("calendar/"), {"from": "2026-09-01", "to": "2026-09-30"})
        self.assertEqual([item["id"] for item in response.data], [f"leave:{leave.pk}", "plugin:1"])
        participants = self.client.get(self.url("calendar/participants/"))
        self.assertEqual({item["id"] for item in participants.data}, {self.reader.pk, self.leader.pk, self.mate.pk})
        self.assertTrue(all(not item["capabilities"]["can_add"] for item in participants.data))
        payload = {"employee_id": self.mate.pk, "type_id": kind.pk, "start_date": "2026-10-01", "start_period": "ST", "end_date": "2026-10-01", "end_period": "EN"}
        self.assertEqual(self.client.post(self.url("calendar/leaves/"), payload, format="json").status_code, 403)
        self.client.force_login(self.other_user)
        self.assertEqual(self.client.post(self.url("calendar/leaves/"), payload, format="json").status_code, 403)
        self.client.force_login(self.user)
        self.grant("staff", "change_employee")
        self.assertEqual(self.client.post(self.url("calendar/leaves/"), payload, format="json").status_code, 201)
        self.assertEqual(self.client.patch(self.url(f"calendar/leaves/{leave.pk}/"), {"comment": "Updated"}, format="json").status_code, 200)
        self.assertEqual(self.client.delete(self.url(f"calendar/leaves/{leave.pk}/")).status_code, 204)

    def test_projects_and_budgets_are_scoped_by_role_and_financial_visibility(self):
        led = Project.objects.create(name="Led")
        colead = Project.objects.create(name="Co-led")
        ordinary = Project.objects.create(name="Ordinary")
        Participant.objects.create(project=led, employee=self.mate, status="l")
        Participant.objects.create(project=led, employee=self.leader, status="cl")
        Participant.objects.create(project=colead, employee=self.reader, status="cl")
        Participant.objects.create(project=ordinary, employee=self.reader, status="p")
        self.grant("project", "view_project")
        projects = self.client.get(self.url("projects/"))
        self.assertEqual([item["name"] for item in projects.data], ["Co-led", "Led"])
        funder = Fund_Institution.objects.create(short_name="ANR", name="Agency")
        institution = Institution.objects.create(short_name="UL", name="University")
        cost = Cost_Type.objects.create(short_name="EQ", name="Equipment")
        funds = [Fund.objects.create(project=project, funder=funder, institution=institution,
                                     start_date=date(2026, 1, 1), end_date=date(2026, 12, 31)) for project in (led, colead, ordinary)]
        for fund in funds:
            Budget.objects.create(fund=fund, cost_type=cost, amount=Decimal("100.00"))
        budgets = self.client.get(self.url("budgets/"))
        self.assertEqual(budgets.status_code, 200, budgets.data)
        self.assertEqual([item["project"]["name"] for item in budgets.data], ["Co-led"])
        self.assertTrue(all(not item["capabilities"]["can_change"] for item in budgets.data))
        self.grant("fund", "view_fund")
        self.grant("fund", "view_budget")
        budgets = self.client.get(self.url("budgets/"))
        self.assertEqual({item["project"]["name"] for item in budgets.data}, {"Co-led", "Led"})
        self.assertNotIn("Ordinary", str(budgets.data))
        self.assertEqual(self.client.post(self.url("budgets/"), {}, format="json").status_code, 405)

    def test_notes_reuse_existing_team_parent(self):
        self.assertEqual(self.client.get(f"/api/v1/notes/team/{self.team.pk}/").status_code, 200)
        self.assertEqual(self.client.get(f"/api/v1/notes/team/{self.hidden_team.pk}/").status_code, 404)
