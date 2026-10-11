from datetime import timedelta
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError as DjangoValidationError
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APITestCase

from endpoints.models import MilestoneDependency, Milestones
from project.models import Participant, Project
from staff.models import Employee


class ProjectPlanningDelayTests(APITestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username="delay-leader", password="test")
        self.employee = Employee.objects.create(first_name="Delay", last_name="Leader", user=self.user)
        self.project = Project.objects.create(name="Delay Project")
        Participant.objects.create(project=self.project, employee=self.employee, status="l")
        self.today = timezone.localdate()
        self.a = self.item("A")
        self.client.force_login(self.user)

    def item(self, name, project=None, *, start=None, end=None, status=False):
        return Milestones.objects.create(name=name, project=project or self.project,
                                         start_date=start, end_date=end if end is not None else self.today,
                                         status=status)

    def edge(self, parent, child):
        return MilestoneDependency.objects.create(predecessor=parent, successor=child)

    def url(self, action):
        return reverse("api_v1:project-planning-delay", kwargs={"pk": self.project.pk, "action": action})

    def preview(self, roots=None, cuts=None, days=14):
        return self.client.post(self.url("preview"), {"root_ids": roots or [self.a.pk],
                                "blocked_dependency_ids": cuts or [], "days": days}, format="json")

    def apply(self, preview):
        return self.client.post(self.url("apply"), {key: preview[key] for key in
                                ("root_ids", "blocked_dependency_ids", "days", "revision")}, format="json")

    def test_single_root_and_date_semantics(self):
        self.a.start_date = self.today - timedelta(days=5)
        self.a.save()
        preview = self.preview().json()
        self.assertEqual(preview["affected"], [{"id": self.a.pk, "old_end_date": str(self.today),
                                                 "new_end_date": str(self.today + timedelta(days=14))}])
        self.assertEqual(self.apply(preview).status_code, 200)
        self.a.refresh_from_db()
        self.assertEqual(self.a.end_date, self.today + timedelta(days=14))
        self.assertEqual(self.a.start_date, self.today - timedelta(days=5))
        for days in (0, -1, 1.5):
            self.assertEqual(self.preview(days=days).status_code, 400)

    def test_chain_propagation_and_cuts(self):
        b, c = self.item("B"), self.item("C")
        ab, bc = self.edge(self.a, b), self.edge(b, c)
        self.assertEqual({row["id"] for row in self.preview().json()["affected"]}, {self.a.pk, b.pk, c.pk})
        first_cut = self.preview(cuts=[ab.pk]).json()
        self.assertEqual({row["id"] for row in first_cut["affected"]}, {self.a.pk})
        self.assertEqual(set(first_cut["excluded_ids"]), {b.pk, c.pk})
        second_cut = self.preview(cuts=[bc.pk]).json()
        self.assertEqual({row["id"] for row in second_cut["affected"]}, {self.a.pk, b.pk})
        self.assertEqual(self.apply(second_cut).status_code, 200)
        self.assertEqual(Milestones.objects.get(pk=c.pk).end_date, self.today)

    def test_branches_multi_roots_and_dag_convergence(self):
        b, c, d = self.item("B"), self.item("C"), self.item("D")
        ac, bc = self.edge(self.a, c), self.edge(b, c)
        self.edge(c, d)
        self.assertEqual({row["id"] for row in self.preview(roots=[self.a.pk, b.pk], cuts=[ac.pk]).json()["affected"]},
                         {self.a.pk, b.pk, c.pk, d.pk})
        both_cut = self.preview(roots=[self.a.pk, b.pk], cuts=[ac.pk, bc.pk]).json()
        self.assertEqual({row["id"] for row in both_cut["affected"]}, {self.a.pk, b.pk})
        full = self.preview(roots=[self.a.pk, b.pk]).json()
        self.assertEqual(len(full["affected"]), 4)
        self.assertEqual(self.apply(full).status_code, 200)
        self.assertEqual(Milestones.objects.get(pk=c.pk).end_date, self.today + timedelta(days=14))

    def test_read_only_descendant_is_excluded_and_no_hidden_label_leaks(self):
        other = Project.objects.create(name="Visible read only")
        Participant.objects.create(project=other, employee=self.employee, status="p")
        child = self.item("Read only child", project=other)
        self.edge(self.a, child)
        hidden = Project.objects.create(name="Secret project")
        secret = self.item("Secret milestone", project=hidden)
        self.edge(self.a, secret)
        preview = self.preview().json()
        self.assertEqual([row["id"] for row in preview["affected"]], [self.a.pk])
        self.assertEqual(next(node["unavailable_reason"] for node in preview["nodes"] if node["id"] == child.pk), "read_only")
        self.assertNotIn("Secret", str(preview))
        self.assertEqual(self.apply(preview).status_code, 200)
        self.assertEqual(Milestones.objects.get(pk=child.pk).end_date, self.today)

    def test_completed_missing_date_and_reader_cannot_delay(self):
        done = self.item("Done", status=True)
        no_end = self.item("No end")
        no_end.end_date = None
        no_end.save()
        self.edge(self.a, done)
        self.edge(self.a, no_end)
        result = self.preview().json()
        self.assertEqual([row["id"] for row in result["affected"]], [self.a.pk])
        self.assertEqual({node["unavailable_reason"] for node in result["nodes"] if node["id"] in (done.pk, no_end.pk)},
                         {"completed", "no_end_date"})
        self.assertEqual(self.preview(roots=[done.pk]).status_code, 400)
        Participant.objects.filter(project=self.project, employee=self.employee).update(status="p")
        self.assertEqual(self.preview().status_code, 403)

    def test_changed_graph_or_deleted_root_rejects_apply(self):
        preview = self.preview().json()
        b = self.item("B")
        self.edge(self.a, b)
        self.assertEqual(self.apply(preview).status_code, 409)
        self.assertEqual(Milestones.objects.get(pk=self.a.pk).end_date, self.today)
        fresh = self.preview().json()
        self.a.delete()
        self.assertEqual(self.apply(fresh).status_code, 400)

    def test_model_validation_rolls_back_all_dates(self):
        b = self.item("B")
        self.edge(self.a, b)
        preview = self.preview().json()
        original = Milestones.full_clean

        def fail_second(item, *args, **kwargs):
            if item.pk == b.pk:
                raise DjangoValidationError({"end_date": "Invalid date"})
            return original(item, *args, **kwargs)

        with patch.object(Milestones, "full_clean", fail_second):
            self.assertEqual(self.apply(preview).status_code, 400)
        self.assertEqual(Milestones.objects.get(pk=self.a.pk).end_date, self.today)
        self.assertEqual(Milestones.objects.get(pk=b.pk).end_date, self.today)
