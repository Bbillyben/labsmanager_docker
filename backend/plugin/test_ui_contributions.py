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
        {"id": "react_action", "slot": "project.detail.actions", "type": "action", "label": "Open demo",
         "behavior": "module", "handler": "run_project", "module": "main", "component": "DemoDialog", "api_version": 1},
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

    def test_detail_slots_and_mixin_registration(self):
        existing = {f"{entity}.detail.{kind}s" for entity in ("project", "employee", "team") for kind in ("action", "section")}
        self.assertEqual(set(SLOTS), existing | {"calendar.toolbar.actions", "published-calendar.actions", "user.plugin.settings.actions", "user.plugin.settings.panels", "plugin.page", *(f"{entity}.detail.tabs" for entity in ("employee", "team", "project"))})
        self.assertEqual(len(self.client.get("/api/v1/ui-contributions/slots/").json()["slots"]), 14)

    def test_react_action_module_is_discovered_and_loaded_only_on_open(self):
        url = self.url("project", self.project, "react_action")
        with patch("plugin.ui_api_v1.module_assets", return_value={
            "module_url": "/static/plugins/alpha/assets/main.js", "css_urls": [], "asset_version": "1",
        }) as assets:
            listed = self.client.get(self.url("project", self.project))
            self.assertEqual(listed.status_code, 200)
            item = next(row for row in listed.json()["contributions"] if row["id"].endswith("react_action"))
            self.assertEqual(item["behavior"], "module")
            self.assertNotIn("module_url", item)
            self.assertEqual(self.plugin.calls, [])
            assets.assert_not_called()
            opened = self.client.get(url)
            self.assertEqual(opened.status_code, 200)
            self.assertEqual(opened.json()["context"], {
                "entity": "project", "objectId": self.project.pk, "name": str(self.project),
                "actionUrl": url,
            })
            self.assertEqual(opened.json()["component"], "DemoDialog")
            self.assertEqual(self.plugin.calls, [])
            assets.assert_called_once()
        with patch("plugin.ui_api_v1.module_assets", side_effect=ValueError("missing")):
            self.assertEqual(self.client.get(url).status_code, 502)
        self.assertEqual(self.client.post(url).status_code, 200)

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
        self.assertEqual(len(identities), 8)
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
            self.assertEqual(len(listed.json()["contributions"]), 3 if entity == "project" else 2)
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

    def test_react_page_and_employee_tab_are_authorized(self):
        self.plugin.UI_CONTRIBUTIONS = [
            {"id": "page", "slot": "plugin.page", "type": "page", "label": "Demo page",
             "module": "main", "component": "Page", "api_version": 1, "visible": "can_show"},
            {"id": "tab", "slot": "employee.detail.tabs", "type": "tab", "label": "Demo tab",
             "module": "main", "component": "EmployeeTab", "api_version": 1, "visible": "can_show"},
        ]
        assets = {"module_url": "/static/plugins/alpha/assets/main-123.js?v=123",
                  "css_urls": ["/static/plugins/alpha/assets/main-123.css?v=123"], "asset_version": "123"}
        with patch("plugin.ui_api_v1.module_assets", return_value=assets) as resolver:
            listed = self.client.get("/api/v1/ui-contributions/pages/")
            self.assertEqual([item["local_id"] for item in listed.json()["contributions"]], ["page"])
            detail = self.client.get("/api/v1/ui-contributions/pages/alpha/page/")
            self.assertEqual(detail.status_code, 200)
            self.assertEqual(detail.json()["module_url"], assets["module_url"])
            self.assertEqual(detail["Cache-Control"], "no-store")
            tab_url = self.url("employee", self.employee, "tab")
            listed = self.client.get(self.url("employee", self.employee))
            self.assertEqual(listed.json()["contributions"][0]["type"], "tab")
            tab = self.client.get(tab_url)
            self.assertEqual(tab.status_code, 200)
            self.assertEqual(tab.json()["context"], {"entity": "employee", "objectId": self.employee.pk})
            self.assertEqual(self.client.get(self.url("employee", self.hidden_employee, "tab")).status_code, 404)
            self.plugin.allowed = False
            self.assertEqual(self.client.get("/api/v1/ui-contributions/pages/alpha/page/").status_code, 404)
            self.assertEqual(self.client.get(tab_url).status_code, 404)
            self.assertEqual(self.client.get("/api/v1/ui-contributions/pages/").json()["contributions"], [])
            self.assertEqual(resolver.call_count, 2)
        with patch.object(registry, "with_mixin", return_value=[]):
            self.assertEqual(self.client.get("/api/v1/ui-contributions/pages/").json()["contributions"], [])
            self.assertEqual(self.client.get("/api/v1/ui-contributions/pages/alpha/page/").status_code, 404)

    def test_page_navigation_metadata_uses_existing_visibility_and_route(self):
        page = {"id": "page", "slot": "plugin.page", "type": "page", "label": "Fallback",
                "module": "main", "component": "Page", "api_version": 1, "visible": "can_show",
                "navigation": {"location": "calendars", "labels": {"fr": "Calendrier", "en": "Calendar"},
                               "icon": "calendar", "order": 2}}
        self.plugin.UI_CONTRIBUTIONS = [page]
        with patch("plugin.ui_api_v1.module_assets") as assets:
            listed = self.client.get("/api/v1/ui-contributions/pages/").json()["contributions"]
            self.assertEqual(listed[0]["id"], "plugin:alpha:page")
            self.assertEqual(listed[0]["navigation"], page["navigation"])
            assets.assert_not_called()
            self.plugin.allowed = False
            self.assertEqual(self.client.get("/api/v1/ui-contributions/pages/").json()["contributions"], [])
            self.assertEqual(self.client.get("/api/v1/ui-contributions/pages/alpha/page/").status_code, 404)
        with patch.object(registry, "with_mixin", return_value=[]):
            self.assertEqual(self.client.get("/api/v1/ui-contributions/pages/").json()["contributions"], [])
        self.plugin.allowed = True
        self.plugin.UI_CONTRIBUTIONS = [{key: value for key, value in page.items() if key != "navigation"}]
        self.assertIsNone(self.client.get("/api/v1/ui-contributions/pages/").json()["contributions"][0]["navigation"])

    def test_page_navigation_rejects_invalid_metadata_without_hiding_other_pages(self):
        page = {"id": "valid", "slot": "plugin.page", "type": "page", "label": "Fallback",
                "module": "main", "component": "Page", "api_version": 1}
        invalid = [
            {"location": "unknown"}, {"location": []},
            {"location": "calendars", "icon": "delete"}, {"location": "calendars", "icon": []},
            {"location": "calendars", "labels": {"fr": " "}},
            {"location": "calendars", "labels": {"de": "Kalender"}},
            {"location": "calendars", "order": True},
            {"location": "calendars", "order": 1001},
            {"location": "calendars", "target": "/admin/"},
        ]
        self.plugin.UI_CONTRIBUTIONS = [page, *({**page, "id": f"bad-{index}", "navigation": data} for index, data in enumerate(invalid))]
        self.assertEqual([item["local_id"] for item in self.client.get("/api/v1/ui-contributions/pages/").json()["contributions"]], ["valid"])
        self.plugin.UI_CONTRIBUTIONS = [{**page, "id": "second", "navigation": {"location": "calendars", "labels": {"fr": "Agenda"}, "order": 0}},
                                        {**page, "navigation": {"location": "calendars", "order": 0}}]
        self.assertEqual([item["id"] for item in self.client.get("/api/v1/ui-contributions/pages/").json()["contributions"]],
                         ["plugin:alpha:second", "plugin:alpha:valid"])

    def test_team_and_project_tabs_use_the_same_visibility_and_direct_route(self):
        self.plugin.UI_CONTRIBUTIONS = [
            {"id": f"{entity}_tab", "slot": f"{entity}.detail.tabs", "type": "tab",
             "label": "Demo tab", "module": "main", "component": "ContextTab", "api_version": 1,
             "visible": "can_show"}
            for entity in ("team", "project")
        ]
        assets = {"module_url": "/static/plugins/alpha/assets/main-123.js?v=123",
                  "css_urls": [], "asset_version": "123"}
        with patch("plugin.ui_api_v1.module_assets", return_value=assets) as resolver:
            for entity, obj, hidden in (("team", self.team, self.hidden_team),
                                        ("project", self.project, self.hidden_project)):
                item_id = f"{entity}_tab"
                listed = self.client.get(self.url(entity, obj))
                self.assertEqual([item["local_id"] for item in listed.json()["contributions"]], [item_id])
                self.assertEqual(resolver.call_count, (0 if entity == "team" else 1))
                detail = self.client.get(self.url(entity, obj, item_id))
                self.assertEqual(detail.status_code, 200)
                self.assertEqual(detail.json()["context"], {"entity": entity, "objectId": obj.pk})
                self.assertEqual(self.client.get(self.url(entity, hidden, item_id)).status_code, 404)
            self.plugin.allowed = False
            self.assertEqual(self.client.get(self.url("team", self.team)).json()["contributions"], [])
            self.assertEqual(self.client.get(self.url("project", self.project, "project_tab")).status_code, 404)

    def test_invalid_react_module_declarations_are_isolated(self):
        self.plugin.UI_CONTRIBUTIONS = [
            {"id": "wrong-api", "slot": "plugin.page", "type": "page", "label": "Bad",
             "module": "main", "component": "Page", "api_version": 2},
            {"id": "remote", "slot": "plugin.page", "type": "page", "label": "Bad",
             "module": "https://example.com/script.js", "component": "Page", "api_version": 1},
        ]
        self.assertEqual(self.client.get("/api/v1/ui-contributions/pages/").json()["contributions"], [])
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

    def test_settings_panel_is_discovered_and_loaded_only_for_its_active_plugin(self):
        self.plugin.UI_CONTRIBUTIONS = [{
            'id': 'settings', 'slot': 'user.plugin.settings.panels', 'type': 'tab',
            'label': 'Settings', 'module': 'main', 'component': 'SettingsPanel', 'api_version': 1,
            'visible': 'can_show',
        }]
        self.plugin.human_name = 'Panel demo'
        self.plugin.description = ''
        self.plugin.mixin_enabled = lambda _name: False
        base = '/api/v1/ui-contributions/user-plugin/alpha/panels/'
        with patch.object(registry, 'plugins', {'alpha': self.plugin}), patch.object(registry, 'check_reload'), \
                patch.object(registry, 'with_mixin', return_value=[self.plugin]), \
                patch.object(registry, 'get_plugin', side_effect=lambda key, active=None: self.plugin if key == 'alpha' else None), \
                patch('plugin.ui_api_v1.module_assets', return_value={
                    'module_url': '/static/plugins/alpha/assets/main.js', 'css_urls': [], 'asset_version': 'abc',
                }):
            results = self.client.get('/api/v1/plugins/mine/').json()['results']
            self.assertEqual([(item['key'], item['ui_panels']) for item in results], [('alpha', True)])
            self.assertEqual([item['local_id'] for item in self.client.get(base).json()['contributions']], ['settings'])
            detail = self.client.get(base + 'settings/')
            self.assertEqual(detail.status_code, 200)
            self.assertEqual(detail.json()['context'], {'pluginKey': 'alpha'})
            self.assertEqual(self.client.get(base + 'missing/').status_code, 404)
            self.assertEqual(self.client.get('/api/v1/ui-contributions/user-plugin/beta/panels/').status_code, 404)
            self.plugin.allowed = False
            self.assertEqual(self.client.get(base).json()['contributions'], [])
            self.assertEqual(self.client.get(base + 'settings/').status_code, 404)
            self.assertEqual(self.client.get('/api/v1/plugins/mine/').json()['results'], [])
        self.client.logout()
        self.assertIn(self.client.get(base).status_code, (401, 403))
