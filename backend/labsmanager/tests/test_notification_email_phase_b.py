from datetime import date, timedelta
from decimal import Decimal
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
from unittest.mock import patch

from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.sites.models import Site
from django.core import mail
from django.template.loader import render_to_string
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone
from django.utils import translation

from labsmanager.email_report import periodic_funding_rows
from labsmanager.email_urls import notification_destination
from labsmanager.mails import SubscriptionMail


class EmployeeStub:
    pk = 7
    user_name = "Alice Martin"

    def __str__(self):
        return self.user_name


class Assigned:
    def __init__(self, items):
        self.items = items

    def all(self):
        return self.items


@override_settings(REACT_PUBLIC_URL="https://frontend.test/app", SITE_ID=1)
class PeriodicEmailTests(TestCase):
    def setUp(self):
        Site.objects.update_or_create(pk=1, defaults={"domain": "backend.test:7000", "name": "LabsManager"})
        self.user = get_user_model().objects.create_user(username="ada", password="secret")
        self.employee = EmployeeStub()
        today = timezone.localdate()
        self.start, self.end = today - timedelta(days=50), today + timedelta(days=50)
        self.project = SimpleNamespace(pk=3, name="Project Atlas", start_date=self.start, end_date=self.end)
        self.funds = [self.fund(11, "F-A", "25"), self.fund(12, "F-B", "50")]

    def fund(self, pk, ref, expense):
        amount = Decimal("100")
        spent = Decimal(expense)
        return SimpleNamespace(pk=pk, project_id=3, project=self.project, ref=ref,
                               funder=SimpleNamespace(short_name="Agency"),
                               institution=SimpleNamespace(short_name="University"),
                               start_date=self.start, end_date=self.end, amount=amount,
                               expense=spent, available=amount - spent, available_f=Decimal("8"))

    def rows(self):
        with patch("labsmanager.email_report.get_project_fund_overviewReport_bytType", return_value=[{
            "type_name": "Personnel", "type_focus": True, "total_amount": 200,
            "total_expense": 75, "total_available": 125,
        }]):
            return periodic_funding_rows([self.project], self.funds)

    def context(self, *, leave_format="list", populated=True):
        projects, funds = self.rows()
        context = {"user": self.user, "sub_status": True, "report_leave": True,
                   "sub_freq": "Weekly", "next_date": self.end, "current_date": self.start,
                   "projects": [self.project] if populated else [], "funds": self.funds if populated else [],
                   "project_report_rows": projects if populated else [], "fund_report_rows": funds if populated else [],
                   "leave_format": leave_format, "days": [self.start, self.start + timedelta(days=1)]}
        if not populated:
            return context
        milestone = SimpleNamespace(name="Ethics approval", project=self.project, project_id=3,
                                    end_date=self.start, quotity=Decimal("0.5"), is_overdue=True,
                                    employee=Assigned([self.employee]))
        contract = SimpleNamespace(employee=self.employee, employee_id=7,
                                   fund=self.funds[0], start_date=self.start, end_date=self.end,
                                   quotity=Decimal("0.8"))
        leave = SimpleNamespace(employee=self.employee, employee_id=7, start_date=self.start,
                                end_date=self.start + timedelta(days=1), type=SimpleNamespace(short_name="Annual"))
        context.update({"project_milestones": [milestone], "employee_milestones": [milestone],
                        "employees": [self.employee], "contracts": [contract],
                        "teams": [SimpleNamespace(pk=9, name="Alpha")], "leave_Alpha": [leave],
                        "leave_emp_Alpha": {self.employee: [leave]},
                        "inc_emp": [{"pk": 7, "user_name": "Alice Martin", "entry_date": self.start,
                                     "exit_date": self.end, "superior": [{"employee_superior": self.employee}],
                                     "status": [{"type": {"shortname": "Postdoc"}}]}],
                        "all_leaves": [leave], "emp_leaves": {self.employee: [leave]},
                        "current_month": "October"})
        return context

    def render(self, **options):
        with patch("plugin.templatetags.plugin_tags.registry.with_mixin", return_value=[]):
            return render_to_string("email/notification_email.html", self.context(**options))

    def test_empty_report_inherits_base_and_keeps_logo(self):
        html = self.render(populated=False)
        self.assertIn('<img src="https://frontend.test/static/img/labsmanager/labsmanager-logo.png"', html)
        self.assertIn('width="48" height="48"', html)
        self.assertNotIn("Project Fund overview", html)
        self.assertIn("Notification settings", html)

    def test_financial_rows_use_visible_funds_and_existing_pace_thresholds(self):
        project_rows, fund_rows = self.rows()
        project = project_rows[0]
        self.assertEqual(project["amount"], 200)
        self.assertEqual(project["expense"], 75)
        self.assertEqual(project["available"], 125)
        self.assertEqual(project["available_focus"], 16)
        self.assertEqual(project["consumption_ratio"], 0.375)
        self.assertEqual(project["temporal_ratio"], 0.5)
        self.assertEqual(project["funding_pace"]["ratio"], 0.75)
        self.assertEqual(project["funding_pace"]["state"], "below")
        self.assertEqual(fund_rows[0]["funding_pace"]["ratio"], 0.5)
        self.assertEqual(fund_rows[1]["funding_pace"]["state"], "aligned")
        ahead = periodic_funding_rows([self.project], [self.fund(13, "F-C", "75")])[1][0]
        self.assertEqual(ahead["funding_pace"]["state"], "above")
        overrun = periodic_funding_rows([self.project], [self.fund(14, "F-D", "150")])[1][0]
        self.assertEqual(overrun["consumption_bar"], 100)
        self.assertEqual(overrun["consumption_ratio"], 1.5)
        self.assertEqual(periodic_funding_rows([self.project], [])[0][0]["amount"], None)

    def test_financial_edge_cases_and_hidden_fund_stay_out_of_report(self):
        zero = self.fund(13, "ZERO", "0")
        zero.amount = Decimal("0")
        zero.start_date = None
        zero.end_date = None
        project_rows, fund_rows = periodic_funding_rows([self.project], [zero])
        self.assertIsNone(fund_rows[0]["consumption_ratio"])
        self.assertIsNone(fund_rows[0]["temporal_ratio"])
        self.assertFalse(fund_rows[0]["funding_pace"]["applicable"])
        self.assertEqual(project_rows[0]["amount"], 0)
        visible_rows, visible_funds = periodic_funding_rows([self.project], self.funds[:1])
        self.assertEqual(visible_rows[0]["amount"], 100)
        self.assertEqual([row["object"].ref for row in visible_funds], ["F-A"])

    def test_all_sections_links_and_list_leaves_remain_visible(self):
        html = self.render()
        for value in ("Project Atlas", "F-A", "F-B", "Agency", "University", "Personnel",
                      "Ethics approval", "Overdue", "Alice Martin", "Postdoc", "Annual", "Alpha",
                      "Budget consumption", "Temporal advancement", "Funding pace", "Available in focus"):
            self.assertIn(value, html)
        self.assertIn("https://frontend.test/app/projects/3/funding", html)
        self.assertIn("https://frontend.test/app/projects/3/tasks", html)
        self.assertIn("https://frontend.test/app/employees/7/", html)
        self.assertIn("https://frontend.test/app/calendars", html)
        self.assertNotIn("/app/app/", html)
        self.assertLess(html.index("Project Milestones"), html.index("Employees Milestones"))
        self.assertNotIn('table-layout:fixed', html)
        self.assertNotIn("None", html)

    def test_calendar_leave_preference_keeps_employee_day_matrix(self):
        html = self.render(leave_format="calendar")
        self.assertEqual(html.count('table-layout:fixed'), 2)
        self.assertIn("Alice Martin", html)
        self.assertIn("×", html)
        self.assertNotIn("ITEMS :", html)

    def test_financial_labels_are_translated_in_french(self):
        with translation.override("fr"):
            html = self.render()
        self.assertIn("Consommation du budget", html)
        self.assertIn("Avancement temporel", html)
        self.assertIn("Rythme de financement", html)

    def test_progress_bar_handles_zero_and_over_100_percent(self):
        zero = render_to_string("email/components/report_progress.html", {
            "label": "Budget consumption", "ratio": 0, "width": 0, "tone": "financial",
        })
        overrun = render_to_string("email/components/report_progress.html", {
            "label": "Budget consumption", "ratio": 1.5, "width": 100, "tone": "financial",
        })
        self.assertNotIn('width="0%"', zero)
        self.assertIn('width="100%"', overrun)
        self.assertIn("150%", overrun)

    def test_plugin_include_and_legacy_link_fallback(self):
        class Plugin:
            @staticmethod
            def get_template():
                return ["plugin_fixture.html"]

        with TemporaryDirectory() as directory:
            (Path(directory) / "plugin_fixture.html").write_text("<p>Plugin: preserved</p>")
            templates = [dict(item) for item in settings.TEMPLATES]
            templates[0]["DIRS"] = [directory, *templates[0]["DIRS"]]
            with override_settings(TEMPLATES=templates), patch(
                "plugin.templatetags.plugin_tags.registry.with_mixin", return_value=[Plugin]
            ):
                html = render_to_string("email/notification_email.html", self.context(populated=False))
        self.assertIn("Plugin: preserved", html)
        with override_settings(REACT_PUBLIC_URL=""):
            self.assertIn(reverse("project_single", kwargs={"pk": 3}), notification_destination("funding", 3))
            self.assertNotIn("/app/", notification_destination("calendar"))

    @override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
    def test_preview_and_real_send_use_same_template_and_embedded_logo(self):
        def setting(key, **kwargs):
            return {"NOTIFCATION_STATUS": False, "NOTIFCATION_FREQ": "daily",
                    "NOTIFCATION_INC_LEAVE": False, "NOTIFCATION_LEAVE_TIMEFRAME": "current",
                    "NOTIFCATION_EMP_INCOMMING": False, "NOTIFCATION_SUB_MILESTONES": False,
                    "NOTIFICATION_ENDPOINTS_MILESTONES_REPORT_REPEAT": 1,
                    "NOTIFICATION_ENDPOINTS_MILESTONES_REPORT_HORIZON": 30,
                    "NOTIFCATION_LEAVE_FORMAT": "list",
                    "NOTIFCATION_LEAVE_REPORT_NONE": False,
                    "NOTIFCATION_REPORT_LANGUAGE": "en"}.get(key)
        with patch("labsmanager.mails.LMUserSetting.get_setting", side_effect=setting), \
             patch("labsmanager.mails.LMUserSetting.get_setting_choices", return_value=[]), \
             patch("settings.models.LabsManagerSetting.get_setting", return_value=""), \
             patch("plugin.registry.registry.with_mixin", return_value=[]), \
             patch("plugin.templatetags.plugin_tags.registry.with_mixin", return_value=[]):
            self.client.force_login(self.user)
            response = self.client.post("/api/v1/settings/notifications/test-email/preview/")
            self.assertEqual(response.status_code, 200)
            self.assertIn(b"Subscription Report", response.content)
            self.assertIn(b'/static/img/labsmanager/labsmanager-logo.png', response.content)
            sent = SubscriptionMail().send("recipient@example.test", user=self.user, embedImg=True)
        self.assertEqual(sent, 1)
        html = mail.outbox[-1].alternatives[0][0]
        image = mail.outbox[-1].attachments[0]
        self.assertIn(f'cid:{image["Content-ID"].strip("<>")}', html)
        self.assertNotIn('/static/img/labsmanager/labsmanager-logo.png', html)
