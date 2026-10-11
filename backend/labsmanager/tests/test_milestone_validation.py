from datetime import date
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.db import IntegrityError, connection, transaction
from django.db.migrations.executor import MigrationExecutor
from django.test import TestCase, TransactionTestCase
from django.urls import reverse
from django.utils import timezone
from django.utils.dateparse import parse_datetime

from endpoints.models import Milestones
from project.models import Project


class MilestoneValidationTests(TestCase):
    def setUp(self):
        self.project = Project.objects.create(name="Validation project")
        self.user = get_user_model().objects.create_user(username="validator-one")
        self.second = get_user_model().objects.create_user(username="validator-two")

    def test_explicit_completion_and_unrelated_save_preserve_validation(self):
        item = Milestones.objects.create(project=self.project, name="Work", quotity=Decimal("0.700"))
        item.status = True
        item.save(validation_user=self.user)
        self.assertEqual(item.quotity, 1)
        self.assertIsNotNone(item.validated_at)
        self.assertEqual(item.validated_by, self.user)
        validated_at = item.validated_at
        item.name = "Renamed"
        item.save()
        self.assertEqual(item.validated_at, validated_at)
        self.assertEqual(item.validated_by, self.user)
        item.refresh_from_db()
        self.assertEqual(item.validated_at, validated_at)

    def test_progress_to_100_reopen_both_ways_and_revalidate(self):
        item = Milestones.objects.create(project=self.project, name="Progress", quotity=Decimal("0.800"))
        item.quotity = Decimal("1.000")
        item.save(validation_user=self.user)
        self.assertTrue(item.status)
        first_date = item.validated_at
        item.quotity = Decimal("0.600")
        item.save(validation_user=self.user)
        self.assertFalse(item.status)
        self.assertIsNone(item.validated_at)
        self.assertIsNone(item.validated_by)
        item.status = True
        item.save(validation_user=self.second)
        self.assertTrue(item.status)
        self.assertEqual(item.quotity, 1)
        self.assertEqual(item.validated_by, self.second)
        self.assertGreaterEqual(item.validated_at, first_date)
        item.status = False
        item.save(validation_user=self.second)
        self.assertFalse(item.status)
        self.assertEqual(item.quotity, 0)
        self.assertIsNone(item.validated_at)
        self.assertIsNone(item.validated_by)

    def test_model_save_without_user_and_api_read_only_validation_fields(self):
        item = Milestones.objects.create(project=self.project, name="Anonymous", quotity=1)
        self.assertTrue(item.status)
        self.assertIsNotNone(item.validated_at)
        self.assertIsNone(item.validated_by)
        with self.assertRaises(IntegrityError), transaction.atomic():
            Milestones.objects.filter(pk=item.pk).update(validated_at=None)
        self.user.user_permissions.add(Permission.objects.get(
            content_type__app_label="project", codename="change_project",
        ))
        self.client.force_login(self.user)
        url = reverse("api_v1:project-planning-item", kwargs={"pk": self.project.pk, "item_id": item.pk})
        response = self.client.patch(url, {
            "name": "Renamed through API", "validated_at": "2000-01-01T00:00:00Z",
            "validated_by": {"id": self.user.pk},
        }, content_type="application/json")
        self.assertEqual(response.status_code, 200, response.content)
        self.assertEqual(parse_datetime(response.json()["validated_at"]), item.validated_at)
        item.refresh_from_db()
        self.assertIsNone(item.validated_by)

    def test_api_completion_and_reopening_record_request_user(self):
        item = Milestones.objects.create(project=self.project, name="API", quotity=Decimal("0.500"))
        self.user.user_permissions.add(Permission.objects.get(
            content_type__app_label="project", codename="change_project",
        ))
        self.client.force_login(self.user)
        url = reverse("api_v1:project-planning-item", kwargs={"pk": self.project.pk, "item_id": item.pk})
        confirmed = self.client.patch(url, '{"quotity":"1.000"}', content_type="application/json")
        self.assertEqual(confirmed.status_code, 200, confirmed.content)
        self.assertTrue(confirmed.json()["status"])
        self.assertEqual(confirmed.json()["validated_by"]["id"], self.user.pk)
        self.assertIsNotNone(confirmed.json()["validated_at"])
        reopened = self.client.patch(url, '{"quotity":"0.300"}', content_type="application/json")
        self.assertEqual(reopened.status_code, 200, reopened.content)
        self.assertFalse(reopened.json()["status"])
        self.assertIsNone(reopened.json()["validated_at"])
        self.assertIsNone(reopened.json()["validated_by"])


class MilestoneValidationMigrationTests(TransactionTestCase):
    def test_historical_backfill_and_undated_reopen(self):
        previous = [("endpoints", "0007_alter_milestones_start_date")]
        current = [("endpoints", "0009_backfill_milestones_validation")]
        MigrationExecutor(connection).migrate(previous)
        try:
            old_apps = MigrationExecutor(connection).loader.project_state(previous).apps
            old_project = old_apps.get_model("project", "Project").objects.create(name="Historical validation")
            old = old_apps.get_model("endpoints", "Milestones")
            dated = old.objects.create(project_id=old_project.pk, name="Dated", status=True, quotity=Decimal("0.600"), end_date=date(2024, 6, 30))
            undated = old.objects.create(project_id=old_project.pk, name="Undated", status=True, quotity=1)
            open_item = old.objects.create(project_id=old_project.pk, name="Open", status=False, quotity=Decimal("0.500"))
            MigrationExecutor(connection).migrate(current)
            dated_new = Milestones.objects.get(pk=dated.pk)
            self.assertEqual(timezone.localtime(dated_new.validated_at).date(), dated.end_date)
            self.assertIsNone(dated_new.validated_by)
            self.assertEqual(dated_new.quotity, 1)
            undated_new = Milestones.objects.get(pk=undated.pk)
            self.assertFalse(undated_new.status)
            self.assertEqual(undated_new.quotity, 0)
            self.assertIsNone(undated_new.validated_at)
            self.assertIsNone(Milestones.objects.get(pk=open_item.pk).validated_at)
        finally:
            MigrationExecutor(connection).migrate(current)
