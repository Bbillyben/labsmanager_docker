"""Django Admin deep links never extend a viewer's object permissions."""

from types import SimpleNamespace
from unittest.mock import Mock

from django.test import SimpleTestCase
from django.urls import reverse
from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase

from expense.models import Contract, Expense, Expense_point
from fund.models import Budget, Contribution, Fund, Fund_Item
from labsmanager.admin_links_v1 import get_admin_change_url
from project.models import Project
from staff.models import Employee, Team, TeamMate
from endpoints.models import Milestones
from leave.models import Leave


def user(*, staff=False, superuser=False, allowed=False):
    return SimpleNamespace(
        is_authenticated=True, is_staff=staff, is_superuser=superuser,
        has_perm=Mock(return_value=allowed),
    )


class AdminChangeLinkTests(SimpleTestCase):
    def test_superuser_gets_registered_model_url_without_permission_lookup(self):
        actor = user(superuser=True)
        employee = Employee(pk=73)
        self.assertEqual(get_admin_change_url(actor, employee), reverse('admin:staff_employee_change', args=[73]))
        actor.has_perm.assert_not_called()

    def test_staff_needs_exact_object_change_permission(self):
        actor = user(staff=True, allowed=True)
        project = Project(pk=42)
        self.assertEqual(get_admin_change_url(actor, project), reverse('admin:project_project_change', args=[42]))
        actor.has_perm.assert_called_once_with('project.change_project', project)
        self.assertIsNone(get_admin_change_url(user(staff=True), project))

    def test_non_staff_never_receives_link_even_with_business_permission(self):
        actor = user(allowed=True)
        self.assertIsNone(get_admin_change_url(actor, Employee(pk=73)))
        actor.has_perm.assert_not_called()

    def test_model_without_admin_change_route_returns_none(self):
        self.assertIsNone(get_admin_change_url(user(superuser=True), TeamMate(pk=5)))

    def test_registered_domain_models_resolve_to_their_own_change_route(self):
        actor = user(superuser=True)
        for model in (Team, Contract, Fund, Budget, Contribution, Leave, Milestones, Expense, Fund_Item, Expense_point):
            with self.subTest(model=model.__name__):
                obj = model(pk=19)
                self.assertEqual(get_admin_change_url(actor, obj), reverse(
                    f'admin:{obj._meta.app_label}_{obj._meta.model_name}_change', args=[19],
                ))


class AdminLinkApiTests(APITestCase):
    def test_employee_and_project_list_and_detail_publish_scoped_urls(self):
        actor = get_user_model().objects.create_superuser(username='admin-links', password='test', email='admin@example.test')
        employee = Employee.objects.create(first_name='Ada', last_name='Lovelace', user=actor)
        project = Project.objects.create(name='Admin links')
        self.client.force_login(actor)
        employee_url = reverse('admin:staff_employee_change', args=[employee.pk])
        project_url = reverse('admin:project_project_change', args=[project.pk])
        employee_list = self.client.get(reverse('api_v1:employees')).json()['results']
        project_list = self.client.get(reverse('api_v1:projects')).json()['results']
        self.assertEqual(next(item for item in employee_list if item['id'] == employee.pk)['admin_url'], employee_url)
        self.assertEqual(next(item for item in project_list if item['id'] == project.pk)['admin_url'], project_url)
        self.assertEqual(self.client.get(reverse('api_v1:employee-detail', args=[employee.pk])).json()['admin_url'], employee_url)
        self.assertEqual(self.client.get(reverse('api_v1:project-detail', args=[project.pk])).json()['admin_url'], project_url)
