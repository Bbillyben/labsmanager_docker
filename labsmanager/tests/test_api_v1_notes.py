"""R2.17: note visibility, parent rules, authorship and mutations."""

from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.contrib.contenttypes.models import ContentType
from django.urls import reverse
from rest_framework.test import APITestCase

from infos.models import GenericNote
from project.models import Participant, Project
from staff.models import Employee, Employee_Superior


class GenericNotesV1Tests(APITestCase):
    def setUp(self):
        User = get_user_model()
        self.owner = User.objects.create_user(username='note-owner')
        self.reader = User.objects.create_user(username='note-reader')
        self.admin = User.objects.create_superuser(username='note-admin', email='admin@example.test', password='x')
        self.employee = Employee.objects.create(first_name='Note', last_name='Owner', user=self.owner)
        self.other = Employee.objects.create(first_name='Other', last_name='Person')
        self.project = Project.objects.create(name='Note Project')
        self.hidden = Project.objects.create(name='Hidden Project')
        Participant.objects.create(project=self.project, employee=self.employee, status='l')
        self.project_url = f'/api/v1/notes/project/{self.project.pk}/'
        self.employee_url = f'/api/v1/notes/employee/{self.employee.pk}/'
        self.client.force_login(self.owner)

    def grant(self, user, app, code):
        user.user_permissions.add(Permission.objects.get(content_type__app_label=app, codename=code))
        for key in ('_perm_cache', '_user_perm_cache', '_group_perm_cache'):
            user.__dict__.pop(key, None)

    def create(self, url, name='General', visibility='object'):
        response = self.client.post(url, {'name': name, 'visibility': visibility}, format='json')
        self.assertEqual(response.status_code, 201, response.content)
        return response.json()

    def test_project_author_visibility_and_collision(self):
        note = self.create(self.project_url)
        self.assertIsNone(note['admin_url'])
        private = self.create(self.project_url, 'Private', 'creator')
        self.assertEqual(GenericNote.objects.get(pk=note['id']).creator, self.owner)
        self.assertEqual(GenericNote.objects.get(pk=note['id']).visibility, 'object')
        collision = self.client.post(self.project_url, {'name': 'General'}, format='json')
        self.assertEqual(collision.status_code, 400)
        self.assertEqual(collision.json()['name'], ['already_exists'])
        self.assertEqual(self.client.post(self.project_url, {'name': 'Forged', 'creator': self.reader.pk}, format='json').status_code, 400)
        self.grant(self.reader, 'project', 'view_project')
        self.client.force_login(self.reader)
        response = self.client.get(self.project_url)
        self.assertEqual([item['id'] for item in response.json()['items']], [note['id']])
        self.assertEqual(self.client.get(f'{self.project_url}{private["id"]}/').status_code, 404)
        self.assertFalse(response.json()['capabilities']['can_add'])
        self.assertEqual(self.client.post(self.project_url, {'name': 'Denied'}, format='json').status_code, 403)
        self.client.force_login(self.admin)
        admin_items = self.client.get(self.project_url).json()['items']
        self.assertEqual(len(admin_items), 2)
        self.assertEqual(next(item for item in admin_items if item['id'] == note['id'])['admin_url'], reverse('admin:infos_genericnote_change', args=[note['id']]))

    def test_private_note_global_admin_and_noncreator_editor(self):
        private = self.create(self.project_url, 'Private', 'creator')
        self.grant(self.reader, 'project', 'view_project')
        self.grant(self.reader, 'project', 'change_project')
        self.client.force_login(self.reader)
        self.assertEqual(self.client.get(f'{self.project_url}{private["id"]}/').status_code, 404)
        self.grant(self.reader, 'infos', 'change_genericnote')
        response = self.client.get(f'{self.project_url}{private["id"]}/')
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()['capabilities']['can_change_visibility'])
        self.assertIsNone(response.json()['admin_url'])
        self.assertEqual(self.client.patch(f'{self.project_url}{private["id"]}/', {'visibility': 'object'}, format='json').status_code, 200)

    def test_object_note_visibility_is_creator_or_admin_only(self):
        created = self.create(self.project_url)
        self.grant(self.reader, 'project', 'view_project')
        self.grant(self.reader, 'project', 'change_project')
        self.client.force_login(self.reader)
        detail = f'{self.project_url}{created["id"]}/'
        self.assertFalse(self.client.get(detail).json()['capabilities']['can_change_visibility'])
        self.assertEqual(self.client.patch(detail, {'visibility': 'creator'}, format='json').status_code, 403)
        self.assertEqual(self.client.patch(detail, {'name': 'Changed'}, format='json').status_code, 200)
        self.assertEqual(self.client.patch(detail, {'creator': self.reader.pk}, format='json').status_code, 400)
        self.assertEqual(GenericNote.objects.get(pk=created['id']).creator, self.owner)
        self.assertEqual(self.client.delete(detail).status_code, 204)

    def test_employee_self_and_superior_without_change_employee(self):
        self.assertFalse(self.owner.has_perm('staff.change_employee', self.employee))
        created = self.create(self.employee_url)
        self.assertEqual(self.client.patch(f'{self.employee_url}{created["id"]}/', {'note': '<p>Safe</p><script>bad()</script>'}, format='json').status_code, 200)
        self.assertNotIn('<script>', GenericNote.objects.get(pk=created['id']).note)
        self.assertEqual(self.client.patch(f'{self.employee_url}{created["id"]}/', {'name': 'Renamed'}, format='json').status_code, 200)
        Employee_Superior.objects.create(employee=self.other, superior=self.employee)
        with patch('staff.rules.LabsManagerSetting.get_setting', return_value=True):
            response = self.client.post(f'/api/v1/notes/employee/{self.other.pk}/', {'name': 'Superior'}, format='json')
            self.assertEqual(response.status_code, 201)

    def test_inaccessible_parent_and_reader_write_denied(self):
        self.assertEqual(self.client.get(f'/api/v1/notes/project/{self.hidden.pk}/').status_code, 404)
        self.grant(self.reader, 'staff', 'view_employee')
        self.client.force_login(self.reader)
        response = self.client.get(self.employee_url)
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.json()['capabilities']['can_add'])
        self.assertEqual(self.client.post(self.employee_url, {'name': 'Denied'}, format='json').status_code, 403)

    def test_existing_note_default_and_separate_parent_names(self):
        note = self.create(self.employee_url)
        self.assertEqual(note['visibility'], 'object')
        self.assertEqual(note['creator']['id'], self.owner.pk)
        second = self.create(self.project_url)
        self.assertNotEqual(note['id'], second['id'])
        self.assertEqual(GenericNote.objects.filter(content_type=ContentType.objects.get_for_model(self.project), object_id=self.project.pk).count(), 1)

    def test_legacy_endpoints_do_not_leak_private_notes_or_accept_forged_parent(self):
        private = self.create(self.project_url, 'Private', 'creator')
        self.grant(self.reader, 'project', 'view_project')
        self.client.force_login(self.reader)
        legacy_list = self.client.get('/api/note/')
        self.assertEqual(legacy_list.status_code, 200)
        self.assertNotIn('Private', str(legacy_list.json()))
        self.assertEqual(self.client.get(f'/api/note/{private["id"]}/').status_code, 404)
        self.assertEqual(self.client.patch(f'/api/note/{private["id"]}/', {'note': 'stolen'}, format='json').status_code, 404)
        scoped = self.client.get(f'/infos/notes/project/project/{self.project.pk}/')
        self.assertEqual(scoped.status_code, 200)
        self.assertNotIn('Private', str(scoped.json()))
