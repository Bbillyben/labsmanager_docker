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
from labsmanager.templatetags.email_tags import leave_calendar_day


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
        self.assertNotIn("None", html)
        self.assertIn("Start Date", html)
        self.assertNotIn('data-leave-calendar="weekly"', html)

    def test_multiple_funds_follow_full_width_project_summary_and_precede_type_detail(self):
        html = self.render()
        block_start = html.index('data-project-financial-block="3"')
        block = html[block_start:html.index("Project Milestones")]
        self.assertLess(block.index("data-project-financial-summary"), block.index("data-project-fund-grid"))
        self.assertLess(block.index("data-project-fund-grid"), block.index("data-project-financial-detail"))
        self.assertEqual(block.count("<tr data-fund-pair>"), 1)
        self.assertIn('data-fund-card="11"', block)
        self.assertIn('data-fund-card="12"', block)
        self.assertIn('width="50%"', block)
        self.assertIn("Personnel", block)
        self.assertIn("F-A", block)
        self.assertIn("F-B", block)
        self.assertEqual(block.count("Budget consumption"), 3)
        self.assertIn("Available in focus", block)
        self.assertIn("Funding pace", block)
        self.assertEqual(block.count('data-fund-metrics="compact"'), 2)
        self.assertIn(".fund-grid-column { display:block !important", html)

    def test_project_without_reported_fund_keeps_its_summary(self):
        project_rows, fund_rows = periodic_funding_rows([self.project], [])
        context = self.context()
        context.update({"project_report_rows": project_rows, "fund_report_rows": fund_rows})
        with patch("plugin.templatetags.plugin_tags.registry.with_mixin", return_value=[]):
            html = render_to_string("email/notification_email.html", context)
        block = html[html.index('data-project-financial-block="3"'):html.index("Project Milestones")]
        self.assertIn("Project Atlas", block)
        self.assertEqual(block.count("Budget consumption"), 1)
        self.assertNotIn("F-A", block)
        self.assertNotIn("data-project-fund-grid", block)
        self.assertNotIn("Project Fund overview", block)

    def test_one_reported_fund_replaces_project_summary_and_keeps_type_detail(self):
        with patch("labsmanager.email_report.get_project_fund_overviewReport_bytType", return_value=[{
            "type_name": "Personnel", "type_focus": True, "total_amount": 100,
            "total_expense": 25, "total_available": 75,
        }]):
            project_rows, fund_rows = periodic_funding_rows([self.project], self.funds[:1])
        context = self.context()
        context.update({"project_report_rows": project_rows, "fund_report_rows": fund_rows})
        with patch("plugin.templatetags.plugin_tags.registry.with_mixin", return_value=[]):
            html = render_to_string("email/notification_email.html", context)
        block = html[html.index('data-project-financial-block="3"'):html.index("Project Milestones")]
        self.assertIn("Project Atlas", block)
        self.assertIn("F-A", block)
        self.assertNotIn("F-B", block)
        self.assertIn("Agency", block)
        self.assertIn("University", block)
        self.assertIn("Personnel", block)
        self.assertEqual(block.count("Budget consumption"), 1)
        self.assertNotIn("data-project-financial-summary", block)
        self.assertNotIn("data-project-fund-grid", block)
        self.assertLess(block.index('data-fund-card="11"'), block.index("data-project-financial-detail"))
        self.assertIn('colspan="2" data-project-financial-detail', block)

    def test_three_and_four_funds_keep_pairs_order_and_last_half_width(self):
        for count in (3, 4):
            with self.subTest(count=count):
                funds = [self.fund(20 + index, f"F-{index + 1}", "10") for index in range(count)]
                funds[-1].ref = "LONG-FUND-REFERENCE-2026-ALPHA"
                with patch("labsmanager.email_report.get_project_fund_overviewReport_bytType", return_value=[{
                    "type_name": "Personnel", "type_focus": True, "total_amount": count * 100,
                    "total_expense": count * 10, "total_available": count * 90,
                }]):
                    project_rows, fund_rows = periodic_funding_rows([self.project], funds)
                context = self.context()
                context.update({"project_report_rows": project_rows, "fund_report_rows": fund_rows})
                with patch("plugin.templatetags.plugin_tags.registry.with_mixin", return_value=[]):
                    html = render_to_string("email/notification_email.html", context)
                block = html[html.index('data-project-financial-block="3"'):html.index("Project Milestones")]
                grid = block[block.index("data-project-fund-grid"):block.index("data-project-financial-detail")]
                pairs = grid.split("<tr data-fund-pair>")[1:]
                self.assertEqual(len(pairs), 2)
                self.assertEqual([pair.count("data-fund-card=") for pair in pairs], [2, count - 2])
                self.assertEqual(grid.count('class="fund-grid-spacer"'), count % 2)
                self.assertEqual([grid.index(f'data-fund-card="{fund.pk}"') for fund in funds], sorted(
                    grid.index(f'data-fund-card="{fund.pk}"') for fund in funds
                ))
                self.assertIn("LONG-FUND-REFERENCE-2026-ALPHA", grid)
                self.assertIn("overflow-wrap:break-word", grid)
                self.assertEqual(block.count("Budget consumption"), count + 1)
                self.assertEqual(block.count('data-fund-metrics="compact"'), count)
                self.assertIn("Personnel", block)

    def test_multiple_projects_keep_their_own_funds_and_type_detail(self):
        second_project = SimpleNamespace(pk=4, name="Project Borealis", start_date=self.start, end_date=self.end)
        second_fund = self.fund(21, "F-C", "10")
        second_fund.project_id = second_project.pk
        second_fund.project = second_project
        summaries = [
            [{"type_name": "Personnel", "type_focus": True, "total_amount": 200,
              "total_expense": 75, "total_available": 125}],
            [{"type_name": "Equipment", "type_focus": False, "total_amount": 100,
              "total_expense": 10, "total_available": 90}],
        ]
        with patch("labsmanager.email_report.get_project_fund_overviewReport_bytType", side_effect=summaries):
            project_rows, fund_rows = periodic_funding_rows(
                [self.project, second_project], [*self.funds, second_fund]
            )
        context = self.context()
        context.update({"projects": [self.project, second_project],
                        "funds": [*self.funds, second_fund],
                        "project_report_rows": project_rows, "fund_report_rows": fund_rows})
        with patch("plugin.templatetags.plugin_tags.registry.with_mixin", return_value=[]):
            html = render_to_string("email/notification_email.html", context)
        first_start = html.index('data-project-financial-block="3"')
        second_start = html.index('data-project-financial-block="4"')
        first_block = html[first_start:second_start]
        second_block = html[second_start:html.index("Project Milestones")]
        self.assertIn("Personnel", first_block)
        self.assertIn("F-A", first_block)
        self.assertIn("F-B", first_block)
        self.assertEqual(first_block.count("Budget consumption"), 3)
        self.assertNotIn("Equipment", first_block)
        self.assertNotIn("F-C", first_block)
        self.assertIn("Equipment", second_block)
        self.assertIn("F-C", second_block)
        self.assertEqual(second_block.count("Budget consumption"), 1)
        self.assertNotIn("data-project-financial-summary", second_block)
        self.assertNotIn("F-A", second_block)

    def test_calendar_leave_preference_keeps_employee_day_matrix(self):
        html = self.render(leave_format="calendar")
        self.assertEqual(html.count('data-leave-calendar="weekly"'), 2)
        self.assertEqual(html.count('data-leave-calendar="desktop"'), 2)
        self.assertIn('width="140"', html)
        self.assertIn("Alice Martin", html)
        self.assertIn('data-coverage="full"', html)
        self.assertNotIn(">×<", html)
        self.assertNotIn("ITEMS :", html)

    def test_calendar_keeps_long_names_order_half_days_and_every_date(self):
        days = [date(2026, 10, 16) + timedelta(days=index) for index in range(10)]
        class CalendarEmployee:
            def __init__(self, pk, name):
                self.pk = pk
                self.name = name

            def __str__(self):
                return self.name

        first = CalendarEmployee(31, "Gerica Olivier Delacroix")
        second = CalendarEmployee(32, "Hanne Devos")
        full = SimpleNamespace(start_date=days[0], end_date=days[2], start_period="ST", end_period="EN")
        half = SimpleNamespace(start_date=days[3], end_date=days[4], start_period="MI", end_period="MI")
        html = render_to_string("email/components/report_leave_calendar.html", {
            "employee_leaves": {first: [full, half], second: []}, "days": days,
        })
        weekly = html.split('data-leave-calendar="desktop"')[0]
        self.assertEqual(weekly.count('class="leave-calendar-grid"'), 2)
        self.assertLess(weekly.index(first.name), weekly.index(second.name))
        self.assertIn("word-break:normal", html)
        self.assertNotIn("break-all", html)
        self.assertEqual(html.count('data-coverage="full"'), 6)
        self.assertEqual(html.count('data-coverage="pm"'), 2)
        self.assertEqual(html.count('data-coverage="am"'), 2)
        for day in days:
            self.assertEqual(html.count(f'data-leave-day="{day.isoformat()}"'), 4)
        self.assertIn("background:#f4f6f8", html)
        self.assertIn("@media only screen and (min-width: 600px)", self.render(leave_format="calendar"))
        self.assertEqual(leave_calendar_day(days[0], [SimpleNamespace(
            start_date=days[0], end_date=days[0], start_period="ST", end_period="MI",
        )]), "am")
        self.assertEqual(leave_calendar_day(days[0], [SimpleNamespace(
            start_date=days[0], end_date=days[0], start_period="MI", end_period="EN",
        )]), "pm")

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
