"""Focused lifecycle consistency detection and correction coverage."""

from datetime import timedelta
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.utils import timezone
from rest_framework.test import APITestCase

from data_consistency.models import DataConsistencyException
from data_consistency.service import RULES_BY_KEY, accepted_exceptions, active_issues
from project.models import Participant, Project
from staff.models import Employee, Team, TeamMate


class LifecycleConsistencyTests(APITestCase):
    def setUp(self):
        self.today = timezone.localdate()
        self.yesterday = self.today - timedelta(days=1)
        self.user = get_user_model().objects.create_user(username="lifecycle-editor")
        self.user.user_permissions.add(*Permission.objects.filter(
            content_type__app_label__in=("staff", "project"),
            codename__in=("view_employee", "view_team", "change_team", "view_project",
                         "change_project")))
        self.user.is_staff = True
        self.user.save(update_fields=["is_staff"])
        self.client.force_login(self.user)
        self.employee = Employee.objects.create(first_name="Alice", last_name="Example")
        self.leader = Employee.objects.create(first_name="Leader", last_name="Example")
        self.team = Team.objects.create(name="Lifecycle team", leader=self.leader)
        self.project = Project.objects.create(name="Lifecycle project")
        Participant.objects.create(project=self.project, employee=self.leader, status="l")

    def issues(self, key):
        response = self.client.get("/api/v1/data-consistency/issues/", {"rule_key": key})
        self.assertEqual(response.status_code, 200, response.data)
        return response.data["results"]

    def correct(self, key, item_id, **identity):
        return self.client.post(f"/api/v1/data-consistency/issues/{key}/{item_id}/correct/",
                                identity, format="json")

    def batch(self, key, **selection):
        return self.client.post(f"/api/v1/data-consistency/issues/{key}/correct-batch/",
                                selection, format="json")

    def test_employee_manual_exit_and_strictly_past_active_exit(self):
        self.employee.is_active = False
        self.employee.save(update_fields=["is_active"])
        key = "inactive_employee_without_exit_date"
        issue = self.issues(key)[0]
        self.assertEqual(issue["employee_id"], self.employee.pk)
        self.assertEqual(issue["manual_url"], f"/employees/{self.employee.pk}")
        summary = self.client.get("/api/v1/data-consistency/summary/").data
        self.assertIsNone(next(row for row in summary["rules"] if row["rule_key"] == key)["correction_action"])
        self.assertEqual(self.batch(key, mode="all", selected_count=1).status_code, 400)
        self.employee.exit_date = self.today
        self.employee.is_active = True
        self.employee.save(update_fields=["exit_date", "is_active"])
        self.assertEqual(self.issues("active_employee_past_exit_date"), [])
        self.employee.exit_date = self.yesterday
        self.employee.save(update_fields=["exit_date"])
        TeamMate.objects.create(team=self.team, employee=self.employee,
                                start_date=self.yesterday - timedelta(days=2))
        Participant.objects.create(project=self.project, employee=self.employee,
                                   start_date=self.yesterday - timedelta(days=2))
        active_key = "active_employee_past_exit_date"
        self.assertEqual(len(self.issues(active_key)), 1)
        response = self.correct(active_key, self.employee.pk, employee_id=self.employee.pk)
        self.assertEqual(response.status_code, 200, response.data)
        self.employee.refresh_from_db()
        self.assertFalse(self.employee.is_active)
        self.assertEqual(self.employee.exit_date, self.yesterday)
        self.assertEqual(self.issues(active_key), [])
        refreshed = self.client.get("/api/v1/data-consistency/summary/").data
        counts = {row["rule_key"]: row["count"] for row in refreshed["rules"]}
        self.assertEqual(counts["inactive_employee_active_team_mate"], 1)
        self.assertEqual(counts["inactive_employee_active_project_participant"], 1)

    def test_inactive_employee_closes_active_memberships_without_overlap(self):
        self.employee.is_active = False
        self.employee.exit_date = self.yesterday
        self.employee.save(update_fields=["is_active", "exit_date"])
        mate = TeamMate.objects.create(team=self.team, employee=self.employee,
                                       start_date=self.yesterday - timedelta(days=10))
        part = Participant.objects.create(project=self.project, employee=self.employee,
                                          start_date=self.yesterday - timedelta(days=10))
        team_key = "inactive_employee_active_team_mate"
        project_key = "inactive_employee_active_project_participant"
        self.assertEqual(len(self.issues(team_key)), 1)
        self.assertEqual(len(self.issues(project_key)), 1)
        self.assertEqual(self.issues("team_mate_after_employee_exit"), [])
        for key in (team_key, project_key):
            result = self.batch(key, mode="all", selected_count=1)
            self.assertEqual(result.status_code, 200, result.data)
            self.assertEqual(result.data["corrected"], 1)
        mate.refresh_from_db(); part.refresh_from_db()
        self.assertEqual(mate.end_date, self.yesterday)
        self.assertEqual(part.end_date, self.yesterday)
        self.assertEqual(self.issues(team_key), [])
        self.assertEqual(self.issues(project_key), [])

    def test_start_checks_keep_employee_dates_and_reject_invalid_periods(self):
        entry = self.today - timedelta(days=5)
        self.employee.entry_date = entry
        self.employee.save(update_fields=["entry_date"])
        mate = TeamMate.objects.create(team=self.team, employee=self.employee,
                                       start_date=entry - timedelta(days=10))
        part = Participant.objects.create(project=self.project, employee=self.employee,
                                          start_date=entry - timedelta(days=10))
        team_key = "team_mate_before_employee_entry"
        project_key = "project_participant_before_employee_entry"
        self.assertEqual(len(self.issues(team_key)), 1)
        self.assertEqual(len(self.issues(project_key)), 1)
        self.assertEqual(self.correct(team_key, mate.pk, employee_id=self.employee.pk, team_id=self.team.pk).status_code, 200)
        self.assertEqual(self.correct(project_key, part.pk, employee_id=self.employee.pk,
                                      project_id=self.project.pk).status_code, 200)
        mate.refresh_from_db(); part.refresh_from_db(); self.employee.refresh_from_db()
        self.assertEqual(mate.start_date, entry)
        self.assertEqual(part.start_date, entry)
        self.assertEqual(self.employee.entry_date, entry)
        mate.start_date = entry - timedelta(days=10)
        mate.end_date = entry - timedelta(days=1)
        mate.save(update_fields=["start_date", "end_date"])
        issue = self.issues(team_key)[0]
        self.assertIsNone(issue["correction_action"])
        result = self.batch(team_key, mode="all", selected_count=1)
        self.assertEqual(result.data["ignored"], 1)
        mate.refresh_from_db()
        self.assertEqual(mate.start_date, entry - timedelta(days=10))

    def test_open_start_respects_existing_participant_validation(self):
        self.employee.is_active = False
        self.employee.exit_date = self.yesterday
        self.employee.save(update_fields=["is_active", "exit_date"])
        mate = TeamMate.objects.create(team=self.team, employee=self.employee)
        part = Participant.objects.create(project=self.project, employee=self.employee)
        team_key = "inactive_employee_active_team_mate"
        project_key = "inactive_employee_active_project_participant"
        self.assertEqual(self.issues(team_key)[0]["correction_action"], "apply_correction")
        self.assertIsNone(self.issues(project_key)[0]["correction_action"])
        self.assertEqual(self.batch(team_key, mode="all", selected_count=1).data["corrected"], 1)
        self.assertEqual(self.batch(project_key, mode="all", selected_count=1).data["ignored"], 1)
        mate.refresh_from_db(); part.refresh_from_db()
        self.assertEqual(mate.end_date, self.yesterday)
        self.assertIsNone(part.end_date)

    def test_end_checks_close_only_exceeding_periods(self):
        self.employee.exit_date = self.yesterday
        self.employee.save(update_fields=["exit_date"])
        self.project.end_date = self.yesterday
        self.project.save(update_fields=["end_date"])
        Participant.objects.filter(project=self.project, employee=self.leader).update(end_date=self.yesterday)
        mate = TeamMate.objects.create(team=self.team, employee=self.employee,
                                       start_date=self.yesterday - timedelta(days=5))
        part = Participant.objects.create(project=self.project, employee=self.employee,
                                          start_date=self.yesterday - timedelta(days=5))
        for key, item in (("team_mate_after_employee_exit", mate),
                          ("project_participant_after_project_end", part)):
            self.assertEqual(len(self.issues(key)), 1)
            result = self.batch(key, mode="all", selected_count=1)
            self.assertEqual(result.status_code, 200, result.data)
            self.assertEqual(result.data["corrected"], 1)
            item.refresh_from_db()
            self.assertEqual(item.end_date, self.yesterday)
            self.assertEqual(self.issues(key), [])

    def test_global_exclusions_revalidation_and_partial_failure(self):
        first = self.employee
        second = Employee.objects.create(first_name="Bob", last_name="Example")
        third = Employee.objects.create(first_name="Cara", last_name="Example")
        for employee in (first, second, third):
            employee.exit_date = self.yesterday
            employee.save(update_fields=["exit_date"])
        key = "active_employee_past_exit_date"
        result = self.batch(key, mode="all", selected_count=2, excluded_ids=[third.pk])
        self.assertEqual(result.data, {"selected": 2, "corrected": 2,
                                       "already_resolved": 0, "ignored": 0, "failed": 0})
        third.refresh_from_db()
        self.assertTrue(third.is_active)
        selected = {"mode": "selected", "selected_count": 1,
                    "issues": [{"id": third.pk, "employee_id": third.pk}]}
        third.is_active = False
        third.save(update_fields=["is_active"])
        self.assertEqual(self.batch(key, **selected).data["already_resolved"], 1)

    def test_new_exception_identities_and_permissions(self):
        self.employee.is_active = False
        self.employee.save(update_fields=["is_active"])
        mate = TeamMate.objects.create(team=self.team, employee=self.employee)
        part = Participant.objects.create(project=self.project, employee=self.employee)
        self.user.user_permissions.add(Permission.objects.get(
            content_type__app_label="data_consistency", codename="add_dataconsistencyexception"))
        for key, object_id, identity in (
            ("inactive_employee_without_exit_date", self.employee.pk, {"employee_id": self.employee.pk}),
            ("inactive_employee_active_team_mate", mate.pk, {"employee_id": self.employee.pk, "team_id": self.team.pk}),
            ("inactive_employee_active_project_participant", part.pk,
             {"employee_id": self.employee.pk, "project_id": self.project.pk}),
        ):
            response = self.client.post(f"/api/v1/data-consistency/issues/{key}/{object_id}/accept/",
                                        identity, format="json")
            self.assertEqual(response.status_code, 201, response.data)
            self.assertEqual(len(self.issues(key)), 0)
            self.assertEqual(len(self.client.get("/api/v1/data-consistency/issues/", {
                "rule_key": key, "status": "accepted"}).data["results"]), 1)
        self.assertEqual(DataConsistencyException.objects.filter(closed_at__isnull=True).count(), 3)

    def test_team_mate_sql_count_and_exception_exclusion(self):
        other = Employee.objects.create(first_name="Bob", last_name="Example", is_active=False)
        self.employee.is_active = False
        self.employee.save(update_fields=["is_active"])
        first = TeamMate.objects.create(team=self.team, employee=self.employee)
        TeamMate.objects.create(team=self.team, employee=other)
        rule = RULES_BY_KEY["inactive_employee_active_team_mate"]

        # Execute the correlated SQL, including the exception table's team_id.
        self.assertEqual(active_issues(self.user, rule).count(), 2)
        self.user.user_permissions.add(Permission.objects.get(
            content_type__app_label="data_consistency", codename="add_dataconsistencyexception"))
        response = self.client.post(
            f"/api/v1/data-consistency/issues/{rule.key}/{first.pk}/accept/",
            {"team_id": self.team.pk, "employee_id": self.employee.pk}, format="json",
        )
        self.assertEqual(response.status_code, 201, response.data)
        self.assertEqual(active_issues(self.user, rule).count(), 1)
        self.assertEqual(accepted_exceptions(self.user, rule).count(), 1)

        response = self.client.get("/api/v1/data-consistency/summary/")
        self.assertEqual(response.status_code, 200, response.data)
        counts = {row["rule_key"]: row["count"] for row in response.data["rules"]}
        self.assertEqual(counts[rule.key], 1)
        self.assertEqual(len(counts), len(RULES_BY_KEY))

    def test_membership_corrections_recheck_change_permission(self):
        self.employee.is_active = False
        self.employee.exit_date = self.yesterday
        self.employee.save(update_fields=["is_active", "exit_date"])
        mate = TeamMate.objects.create(team=self.team, employee=self.employee)
        part = Participant.objects.create(project=self.project, employee=self.employee)
        self.user.user_permissions.remove(*Permission.objects.filter(
            content_type__app_label__in=("staff", "project"),
            codename__in=("change_team", "change_project")))
        self.user = get_user_model().objects.get(pk=self.user.pk)
        self.client.force_login(self.user)
        for key, item in (("inactive_employee_active_team_mate", mate),
                          ("inactive_employee_active_project_participant", part)):
            issue = self.issues(key)[0]
            self.assertIsNone(issue["correction_action"])
            result = self.batch(key, mode="all", selected_count=1)
            self.assertEqual(result.status_code, 200, result.data)
            self.assertEqual(result.data["ignored"], 1)
            item.refresh_from_db()
            self.assertIsNone(item.end_date)

    def test_lifecycle_batch_keeps_success_after_one_failure(self):
        second = Employee.objects.create(first_name="Bob", last_name="Example")
        for employee in (self.employee, second):
            employee.exit_date = self.yesterday
            employee.save(update_fields=["exit_date"])
        from data_consistency.corrections import correct_lifecycle_issue

        def correct_or_fail(request, rule, object_id, expected=None):
            if object_id == second.pk:
                raise RuntimeError("Simulated lifecycle failure")
            return correct_lifecycle_issue(request, rule, object_id, expected)

        key = "active_employee_past_exit_date"
        with patch("data_consistency.api_v1.correct_lifecycle_issue", side_effect=correct_or_fail):
            result = self.batch(key, mode="all", selected_count=2)
        self.assertEqual(result.status_code, 200, result.data)
        self.assertEqual(result.data, {"selected": 2, "corrected": 1,
                                       "already_resolved": 0, "ignored": 0, "failed": 1})
        self.employee.refresh_from_db(); second.refresh_from_db()
        self.assertFalse(self.employee.is_active)
        self.assertTrue(second.is_active)
