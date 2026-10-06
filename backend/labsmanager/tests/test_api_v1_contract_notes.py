"""Contract Notes use the shared Notes API and scoped Contract summaries."""

from django.contrib.auth import get_user_model
from django.contrib.contenttypes.models import ContentType
from rest_framework.test import APITestCase

from expense.models import Contract
from infos.models import GenericNote

from .test_api_v1_funding import ProjectFundingV1Tests


class ContractNotesV1Tests(APITestCase):
    def setUp(self):
        ProjectFundingV1Tests.setUp(self)
        self.worker = self.employee
        self.contract = Contract.objects.create(employee=self.worker, fund=self.fund, status='prov')
        self.hidden_contract = Contract.objects.create(employee=self.worker, fund=self.hidden_fund, status='prov')
        self.other = get_user_model().objects.create_user(username='other-note-author')
        self.notes_url = f'/api/v1/notes/contract/{self.contract.pk}/'
        self.project_url = f'/api/v1/projects/{self.project.pk}/contracts/'
        self.employee_url = f'/api/v1/employees/{self.worker.pk}/contracts/'

    def grant(self, code, app):
        ProjectFundingV1Tests.grant(self, code, app)

    def add_note(self, name, visibility='object', creator=None):
        return GenericNote.objects.create(
            content_type=ContentType.objects.get_for_model(Contract), object_id=self.contract.pk,
            name=name, note='<p>Text</p>', visibility=visibility, creator=creator or self.user,
        )

    def test_contract_parent_visibility_and_private_counts_in_both_contexts(self):
        self.add_note('Public')
        self.add_note('Own private', 'creator')
        other_private = self.add_note('Other private', 'creator', self.other)
        self.assertEqual(self.client.get(self.notes_url).status_code, 200)
        self.assertEqual([item['name'] for item in self.client.get(self.notes_url).data['items']], ['Public', 'Own private'])
        self.assertEqual(self.client.get(f'{self.notes_url}{other_private.pk}/').status_code, 404)
        project = self.client.get(self.project_url)
        self.assertEqual(project.status_code, 200)
        self.assertEqual(project.data['items'][0]['notes'], {'visible_count': 2, 'can_add': False})
        self.grant('view_employee', 'staff')
        employee = self.client.get(self.employee_url)
        self.assertEqual(employee.status_code, 200)
        self.assertEqual(employee.data[0]['notes'], project.data['items'][0]['notes'])
        self.client.force_login(self.other)
        self.assertEqual(self.client.get(f'/api/v1/notes/contract/{self.hidden_contract.pk}/').status_code, 404)

    def test_canonical_contract_permission_controls_mutations_and_summary(self):
        denied = self.client.post(self.notes_url, {'name': 'First'}, format='json')
        self.assertEqual(denied.status_code, 403)
        self.grant('self_edit', 'common')
        self.assertTrue(self.user.has_perm('project.change_project', self.project))
        self.assertTrue(self.user.has_perm('staff.change_employee', self.worker))
        self.assertTrue(self.user.has_perm('expense.change_contract', self.contract))
        self.assertTrue(self.client.get(self.project_url).data['items'][0]['notes']['can_add'])
        self.assertTrue(self.client.get(self.employee_url).data[0]['notes']['can_add'])
        created = self.client.post(self.notes_url, {'name': 'First'}, format='json')
        self.assertEqual(created.status_code, 201, created.data)
        detail = f'{self.notes_url}{created.data["id"]}/'
        self.assertEqual(self.client.patch(detail, {'note': '<p>Changed</p>'}, format='json').status_code, 200)
        self.add_note('Second')
        self.assertEqual(self.client.get(self.project_url).data['items'][0]['notes']['visible_count'], 2)
        self.assertEqual(self.client.delete(detail).status_code, 204)
        self.assertEqual(self.client.get(self.project_url).data['items'][0]['notes']['visible_count'], 1)

    def test_admin_sees_private_note_and_zero_count_is_safe(self):
        self.assertEqual(self.client.get(self.project_url).data['items'][0]['notes'], {'visible_count': 0, 'can_add': False})
        self.add_note('Other private', 'creator', self.other)
        self.assertEqual(self.client.get(self.project_url).data['items'][0]['notes']['visible_count'], 0)
        self.grant('change_genericnote', 'infos')
        self.assertEqual(self.client.get(self.project_url).data['items'][0]['notes'], {'visible_count': 1, 'can_add': True})
        self.assertEqual([item['name'] for item in self.client.get(self.notes_url).data['items']], ['Other private'])
