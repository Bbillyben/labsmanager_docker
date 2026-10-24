"""Targeted contract and access tests for React plugin contributions."""

from unittest.mock import patch

from django.contrib.auth import get_user_model
from rest_framework.exceptions import PermissionDenied
from rest_framework.test import APIClient, APITestCase

from plugin.base.UIContributionMixin import UIContributionMixin
from plugin.registry import registry
from plugin.ui_contributions import SLOTS, declared_contributions
from common.calendar import CalendarContext, CalendarType
from project.models import Participant, Project
from staff.models import Employee, Team


class DemoPlugin:
    slug = "alpha"
    allowed = True
    calls = None
    UI_CONTRIBUTIONS = [
        {"id": "shared", "slot": "project.detail.actions", "type": "action", "label": "Copy Project",
         "behavior": "copy_url", "handler": "run_project", "visible": "can_show"},
        {"id": "project_section", "slot": "project.detail.sections", "type": "section",
         "label": "Project facts", "handler": "project_section"},
        {"id": "employee_action", "slot": "employee.detail.actions", "type": "action",
         "label": "Employee action", "handler": "run_employee"},
        {"id": "employee_section", "slot": "employee.detail.sections", "type": "section",
         "label": "Employee facts", "handler": "employee_section"},
        {"id": "team_action", "slot": "team.detail.actions", "type": "action", "label": "Open Team",
         "behavior": "open_url", "handler": "run_team"},
        {"id": "team_section", "slot": "team.detail.sections", "type": "section",
         "label": "Team facts", "handler": "team_section"},
    ]

    def can_show(self, request, context):
        return self.allowed

    def record(self, request, context, entity):
        self.calls.append((request.user.username, context[entity].pk, context["contribution"]["id"]))

    def run_project(self, request, context):
        self.record(request, context, "project")
        return {"url": f"/app/projects/{context['project'].pk}"}

    def project_section(self, request, context):
        self.record(request, context, "project")
        return {"format": "properties", "items": [{"label": "User", "value": request.user.username}]}

    def run_employee(self, request, context):
        self.record(request, context, "employee")
        return {"message": str(context["employee"].pk)}

    def employee_section(self, request, context):
        self.record(request, context, "employee")
        return {"format": "items", "items": [{"label": request.user.username}]}

    def run_team(self, request, context):
        self.record(request, context, "team")
        return {"url": f"/app/teams/{context['team'].pk}"}

    def team_section(self, request, context):
        self.record(request, context, "team")
        return {"format": "links", "items": [{"label": request.user.username, "url": "/app/teams"}]}


class UIContributionTests(APITestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username="plugin-reader")
        self.employee = Employee.objects.create(first_name="Ada", last_name="Reader", user=self.user)
        self.hidden_employee = Employee.objects.create(first_name="Hidden", last_name="Person")
        self.project = Project.objects.create(name="Visible")
        self.hidden_project = Project.objects.create(name="Hidden")
        Participant.objects.create(project=self.project, employee=self.employee, status="p")
        self.team = Team.objects.create(name="Visible", leader=self.employee)
        self.hidden_team = Team.objects.create(name="Hidden", leader=self.hidden_employee)
        self.plugin = DemoPlugin()
        self.plugin.calls = []
        self.registry_patch = patch.object(registry, "with_mixin", return_value=[self.plugin])
        self.registry_patch.start()
        self.addCleanup(self.registry_patch.stop)
        self.client.force_login(self.user)

    def url(self, entity, obj, contribution=None):
        base = f"/api/v1/ui-contributions/{entity}/{obj.pk}/"
        return base + (f"plugin:alpha:{contribution}/" if contribution else "")

    def test_eight_slots_and_mixin_registration(self):
        existing = {f"{entity}.detail.{kind}s" for entity in ("project", "employee", "team") for kind in ("action", "section")}
        self.assertEqual(set(SLOTS), existing | {"calendar.toolbar.actions", "user.plugin.settings.actions"})
        self.assertEqual(len(self.client.get("/api/v1/ui-contributions/slots/").json()["slots"]), 8)

        class Standalone(UIContributionMixin):
            def add_mixin(self, key, enabled, cls):
                self.registered = (key, enabled, cls)

        self.assertEqual(Standalone().registered[:2], ("uicontribution", True))

    def test_registration_isolated_and_global_id_contains_slug(self):
        other = DemoPlugin()
        other.slug = "beta"
        other.UI_CONTRIBUTIONS = [self.plugin.UI_CONTRIBUTIONS[0]]
        malformed = [
            {"id": "unknown", "slot": "contract.detail.actions", "type": "action", "label": "Bad", "handler": "run_project"},
            {"id": "wrong", "slot": "project.detail.actions", "type": "section", "label": "Bad", "handler": "run_project"},
            {"id": "missing", "slot": "project.detail.actions", "type": "action", "label": "Bad", "handler": "does_not_exist"},
            self.plugin.UI_CONTRIBUTIONS[0],
        ]
        self.plugin.UI_CONTRIBUTIONS = [*self.plugin.UI_CONTRIBUTIONS, *malformed]
        with patch.object(registry, "with_mixin", return_value=[self.plugin, other]):
            identities = [item["id"] for _, item in declared_contributions()]
        self.assertIn("plugin:alpha:shared", identities)
        self.assertIn("plugin:beta:shared", identities)
        self.assertEqual(identities.count("plugin:alpha:shared"), 1)
        self.assertEqual(len(identities), 7)
        with patch.object(registry, "with_mixin", return_value=[]) as active_plugins:
            self.assertEqual(self.client.get(self.url("project", self.project)).json()["contributions"], [])
            active_plugins.assert_called_with("uicontribution", active=True)

    def test_handlers_receive_current_user_and_visible_business_objects(self):
        for entity, obj, action, section in [
            ("project", self.project, "shared", "project_section"),
            ("employee", self.employee, "employee_action", "employee_section"),
            ("team", self.team, "team_action", "team_section"),
        ]:
            listed = self.client.get(self.url(entity, obj))
            self.assertEqual(listed.status_code, 200)
            self.assertEqual(len(listed.json()["contributions"]), 2)
            self.assertEqual(self.client.get(self.url(entity, obj, section)).status_code, 200)
            action_response = self.client.post(self.url(entity, obj, action))
            self.assertEqual(action_response.status_code, 200)
            self.assertEqual(action_response["Cache-Control"], "no-store")
        self.assertEqual(len(self.plugin.calls), 6)
        self.assertTrue(all(user == self.user.username for user, _, _ in self.plugin.calls))
        self.assertIn((self.user.username, self.project.pk, "plugin:alpha:shared"), self.plugin.calls)

    def test_hidden_objects_and_visibility_are_enforced_on_direct_calls(self):
        for entity, obj, action, section in [
            ("project", self.hidden_project, "shared", "project_section"),
            ("employee", self.hidden_employee, "employee_action", "employee_section"),
            ("team", self.hidden_team, "team_action", "team_section"),
        ]:
            self.assertEqual(self.client.get(self.url(entity, obj)).status_code, 404)
            self.assertEqual(self.client.get(self.url(entity, obj, section)).status_code, 404)
            self.assertEqual(self.client.post(self.url(entity, obj, action)).status_code, 404)
        self.assertEqual(self.client.get(self.url("project", self.project)).status_code, 200)
        self.plugin.allowed = False
        self.assertEqual(self.client.post(self.url("project", self.project, "shared")).status_code, 404)
        self.assertEqual(self.plugin.calls, [])

    def test_handler_failure_is_local_and_arbitrary_method_is_not_callable(self):
        self.plugin.project_section = lambda request, context: 1 / 0
        self.assertEqual(self.client.get(self.url("project", self.project, "project_section")).status_code, 502)
        self.assertEqual(self.client.post(self.url("project", self.project, "shared")).status_code, 200)
        self.assertEqual(self.client.post(self.url("project", self.project, "delete_everything")).status_code, 404)
        self.assertEqual(self.client.get(self.url("project", self.project)).status_code, 200)

    def test_plugin_cannot_return_executable_urls(self):
        self.plugin.run_project = lambda request, context: {"url": "javascript:alert(1)"}
        self.plugin.project_section = lambda request, context: {"format": "links", "items": [
            {"label": "Unsafe", "url": "javascript:alert(1)"}]}
        self.assertEqual(self.client.post(self.url("project", self.project, "shared")).status_code, 502)
        self.assertEqual(self.client.get(self.url("project", self.project, "project_section")).status_code, 502)

    def test_handler_can_enforce_a_stronger_action_permission(self):
        def denied(request, context):
            raise PermissionDenied("Extra permission required")

        self.plugin.run_project = denied
        self.assertEqual(self.client.get(self.url("project", self.project)).status_code, 200)
        self.assertEqual(self.client.post(self.url("project", self.project, "shared")).status_code, 403)

    def test_anonymous_requests_do_not_disclose_contributions(self):
        self.client.logout()
        self.assertIn(self.client.get(self.url("project", self.project)).status_code, (401, 403))
        self.assertIn(self.client.post(self.url("project", self.project, "shared")).status_code, (401, 403))

    def test_action_requires_session_csrf(self):
        client = APIClient(enforce_csrf_checks=True)
        client.force_login(self.user)
        self.assertEqual(client.get(self.url("project", self.project)).status_code, 200)
        self.assertEqual(client.post(self.url("project", self.project, "shared")).status_code, 403)
        self.assertEqual(self.plugin.calls, [])

    def test_calendar_contexts_and_permissions(self):
        self.assertEqual(self.client.get('/api/v1/ui-contributions/calendar/0/').status_code, 404)
        self.assertEqual(self.client.get('/api/v1/ui-contributions/user-plugin/0/').status_code, 404)
        received = []
        def action(request, context):
            calendar = context['calendar_context']
            self.assertIsInstance(calendar, CalendarContext)
            self.assertEqual(calendar.user, request.user)
            received.append((request.user.username, calendar.calendar_type, context['calendar_id']))
            return {'message': 'Done'}
        self.plugin.calendar_action = action
        self.plugin.UI_CONTRIBUTIONS = [
            {'id': 'first', 'slot': 'calendar.toolbar.actions', 'type': 'action', 'label': 'First', 'handler': 'calendar_action'},
            {'id': 'second', 'slot': 'calendar.toolbar.actions', 'type': 'action', 'label': 'Second', 'handler': 'calendar_action'},
        ]
        for name, obj, expected in [
            ('main', 0, CalendarType.MAIN), ('project_all', 0, CalendarType.PROJECT_ALL),
            ('project', self.project.pk, CalendarType.PROJECT),
            ('employee', self.employee.pk, CalendarType.EMPLOYEE),
            ('team', self.team.pk, CalendarType.TEAM),
        ]:
            base = f'/api/v1/ui-contributions/calendar/{name}/{obj}/'
            self.assertEqual(len(self.client.get(base).json()['contributions']), 2)
            self.assertEqual(self.client.post(base + 'plugin:alpha:first/').status_code, 200)
            self.assertEqual(received[-1], (self.user.username, expected, obj or None))
        for name, obj in [('project', self.hidden_project.pk), ('employee', self.hidden_employee.pk), ('team', self.hidden_team.pk), ('main', 1), ('invalid', 0)]:
            base = f'/api/v1/ui-contributions/calendar/{name}/{obj}/'
            self.assertEqual(self.client.get(base).status_code, 404)
            self.assertEqual(self.client.post(base + 'plugin:alpha:first/').status_code, 404)
        with patch.object(registry, 'with_mixin', return_value=[]):
            self.assertEqual(self.client.get('/api/v1/ui-contributions/calendar/main/0/').json()['contributions'], [])

    def test_personal_actions_belong_to_the_page_plugin(self):
        other = DemoPlugin()
        other.slug = 'beta'
        calls = []
        def action(request, context):
            self.assertEqual(context['plugin'], self.plugin)
            self.assertEqual(context['plugin_key'], 'alpha')
            calls.append(request.user.username)
            return {'message': 'Done'}
        self.plugin.personal_action = action
        self.plugin.UI_CONTRIBUTIONS = [
            {'id': value, 'slot': 'user.plugin.settings.actions', 'type': 'action',
             'label': value, 'handler': 'personal_action'} for value in ('first', 'second')]
        other.UI_CONTRIBUTIONS = [dict(self.plugin.UI_CONTRIBUTIONS[0], handler='run_project')]
        plugins = {'alpha': self.plugin, 'beta': other}
        with patch.object(registry, 'with_mixin', return_value=[self.plugin, other]), \
                patch.object(registry, 'get_plugin', side_effect=lambda key, active=None: plugins.get(key)):
            base = '/api/v1/ui-contributions/user-plugin/alpha/'
            self.assertEqual([item['id'] for item in self.client.get(base).json()['contributions']],
                             ['plugin:alpha:first', 'plugin:alpha:second'])
            self.assertEqual(self.client.post(base + 'plugin:alpha:first/').status_code, 200)
            self.assertEqual(self.client.post(base + 'plugin:beta:first/').status_code, 404)
            self.assertEqual(self.client.get('/api/v1/ui-contributions/user-plugin/missing/').status_code, 404)
            self.assertEqual(calls, [self.user.username])

    def test_action_only_plugin_is_discovered_when_active(self):
        self.plugin.UI_CONTRIBUTIONS = [{
            'id': 'copy', 'slot': 'user.plugin.settings.actions', 'type': 'action',
            'label': 'Copy', 'handler': 'run_project', 'behavior': 'copy_url',
        }]
        self.plugin.human_name = 'Action demo'
        self.plugin.description = ''
        self.plugin.mixin_enabled = lambda _name: False
        with patch.object(registry, 'plugins', {'alpha': self.plugin}), patch.object(registry, 'check_reload'):
            results = self.client.get('/api/v1/plugins/mine/').json()['results']
            self.assertEqual([(item['key'], item['ui_actions']) for item in results], [('alpha', True)])
            with patch.object(registry, 'with_mixin', return_value=[]):
                self.assertEqual(self.client.get('/api/v1/plugins/mine/').json()['results'], [])
