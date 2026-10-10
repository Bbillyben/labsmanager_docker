from datetime import date
from copy import deepcopy
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
from unittest.mock import patch
from django.urls import reverse

from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.sites.models import Site
from django.contrib.staticfiles import finders
from django.core import mail
from django.template.loader import render_to_string
from django.test import TestCase, override_settings
from django.utils import translation

from labsmanager.email_urls import django_email_url, notification_destination
from labsmanager.mails import BaseMail
from notification.mails import NotificationMail


class People:
    def __init__(self, *items):
        self.items = items

    def all(self):
        return self.items


def note(source, action, message, model="milestones"):
    return SimpleNamespace(
        source_object=source, source_content_type=SimpleNamespace(app_label="endpoints", model=model),
        action_type=action, message=message, get_action_type_display=lambda: "Add" if action == "add" else "Remove",
    )


@override_settings(REACT_PUBLIC_URL="https://frontend.test/app", SITE_ID=1)
class NotificationEmailPhaseATests(TestCase):
    def setUp(self):
        Site.objects.update_or_create(pk=1, defaults={"domain": "backend.test:7000", "name": "LabsManager"})
        self.user = get_user_model().objects.create_user(username="ada")
        self.project = SimpleNamespace(pk=3, id=3, name="Project Atlas")
        self.people = People(SimpleNamespace(first_name="Alice", last_name="Martin"), SimpleNamespace(first_name="Bob", last_name="Dupont"))
        self.milestone = SimpleNamespace(pk=11, name="Ethics approval", start_date=None, end_date=date(2026, 10, 12), project=self.project, project_id=3, employee=self.people)
        self.task = SimpleNamespace(pk=12, name="Prepare samples", start_date=date(2026, 10, 1), end_date=date(2026, 10, 15), project=self.project, project_id=3, employee=People())
        self.participant = SimpleNamespace(project=self.project, project_id=3)
        self.employee = SimpleNamespace(pk=7, user_name="Alice Martin")

    def render(self, notifications=None):
        context = {
            "user": self.user,
            "notification": notifications or {},
            "sub_status": True, "milestone_enab": True, "milestone_stale": 5,
            "milestone_repeat": 7, "participant_enab": True, "employee_enab": False,
        }
        with patch("plugin.templatetags.plugin_tags.registry.with_mixin", return_value=[]):
            return render_to_string("email/usernotification_email.html", context)

    def test_base_html_logo_and_periodic_template_remain_compatible(self):
        html = self.render()
        self.assertIn("<!doctype html>", html.lower())
        self.assertLess(html.index("<html"), html.index("<head"))
        self.assertLess(html.index("<head"), html.index("<style"))
        self.assertIn('<meta charset="utf-8">', html)
        self.assertIn('src="https://frontend.test/static/img/labsmanager/labsmanager-logo.png"', html)
        self.assertIn('alt="LabsManager"', html)
        self.assertIn("Sent by LabsManager", html)
        self.assertIn("https://frontend.test/app/settings/notifications", html)
        self.assertTrue((Path(settings.BASE_DIR) / "data/static/img/labsmanager/labsmanager-logo.png").exists())
        self.assertTrue(finders.find("img/labsmanager/labsmanager-logo.png"))
        with patch("plugin.templatetags.plugin_tags.registry.with_mixin", return_value=[]):
            old = render_to_string("email/notification_email.html", {"user": self.user, "notification": {}})
        self.assertIn("<!doctype html>", old.lower())
        self.assertIn("LabsManager", old)
        self.assertNotIn(".main-container", BaseMail().render_body(old))

    @override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
    def test_notification_mail_embeds_logo_without_remote_image(self):
        with patch("notification.mails.UserNotification.objects.filter", return_value=[]), \
             patch("notification.mails.LMUserSetting.get_setting", side_effect=lambda key, **kwargs: "en" if key == "NOTIFCATION_REPORT_LANGUAGE" else True), \
             patch("settings.models.LabsManagerSetting.get_setting", return_value=""), \
             patch("plugin.registry.registry.with_mixin", return_value=[]), \
             patch("plugin.templatetags.plugin_tags.registry.with_mixin", return_value=[]):
            result = NotificationMail().send("recipient@example.test", user=self.user.pk, embedImg=True)

        self.assertEqual(result, 1)
        sent = mail.outbox[-1]
        html = sent.alternatives[0][0]
        self.assertNotIn("https://frontend.test/static/img/labsmanager/labsmanager-logo.png", html)
        self.assertNotIn('src="/static/img/labsmanager/labsmanager-logo.png"', html)
        self.assertEqual(len(sent.attachments), 1)
        image = sent.attachments[0]
        self.assertEqual(image.get_content_maintype(), "image")
        self.assertIn(f'src="cid:{image["Content-ID"].strip("<>")}"', html)

    def test_action_badges_cover_all_codes_and_unknowns(self):
        labels = {
            "add": "Updated", "rem": "Unassigned", "sta": "Stale", "ove": "Overdue",
            "com": "Completed", "del": "Deleted", "res": "Rescheduled", "ovl": "Overload",
            None: "Notification", "xxx": "Unknown event",
        }
        for action, label in labels.items():
            with self.subTest(action=action):
                html = self.render({"endpoints_milestones": [note(self.milestone, action, "Original message")]})
                self.assertIn(label, html)
                self.assertIn("Original message", html)
                if action == "add":
                    self.assertNotIn("Assigned to you", html)
                    self.assertNotIn("A new milestone was created", html)
                if action == "rem":
                    self.assertNotIn("The milestone was removed", html)

        with translation.override("fr"):
            french = self.render({"endpoints_milestones": [note(self.milestone, "rem", "Message métier")]})
        self.assertIn('lang="fr"', french)
        self.assertIn("Désaffecté", french)
        self.assertIn("Message métier", french)

    def test_full_and_sparse_cards_multiple_sections_and_react_links(self):
        long_title = "Long task title " * 10
        long_message = "Long original message " * 20
        task = SimpleNamespace(**{**vars(self.task), "name": long_title})
        sparse = SimpleNamespace(name="Sparse task", start_date=date(2026, 10, 1), end_date=None, project=None, project_id=None, employee=People())
        html = self.render({
            "endpoints_milestones": [note(self.milestone, "ove", "Due soon"), note(task, "rem", long_message), note(sparse, None, None)],
            "project_participant": [note(self.participant, "add", "Project membership changed", "participant")],
            "staff_employee": [note(self.employee, "add", "Employee changed", "employee")],
        })
        for expected in ("Ethics approval", long_title, long_message, "Sparse task", "Alice Martin", "Bob Dupont", "No assigned employees", "Project Atlas", "Project membership changed", "Employee changed"):
            self.assertIn(expected, html)
        self.assertIn("Task", html)
        self.assertIn("Milestone", html)
        self.assertIn("https://frontend.test/app/projects/3/tasks", html)
        self.assertIn("https://frontend.test/app/projects/3/", html)
        self.assertIn("https://frontend.test/app/employees/7/", html)
        self.assertNotIn("/app/app/", html)
        self.assertNotIn("None</div>", html)
        self.assertEqual(html.count("Due date"), 2)

    def test_url_helper_uses_react_and_legacy_fallback(self):
        self.assertEqual(notification_destination("planning", 3), "https://frontend.test/app/projects/3/tasks")
        self.assertEqual(notification_destination("settings"), "https://frontend.test/app/settings/notifications")
        with override_settings(REACT_PUBLIC_URL=""):
            self.assertEqual(notification_destination("project", 3), django_email_url(reverse("project_single", kwargs={"pk": 3})))
            self.assertTrue(notification_destination("employee", 7).startswith("http://backend.test:7000/"))

    def test_notification_mail_preserves_plugin_context_and_template_inclusion(self):
        class Plugin:
            slug = "example"

            @staticmethod
            def add_context(user, context):
                return {"message": "Plugin content"}

            @staticmethod
            def get_template():
                return ["plugin_fixture.html"]

        with TemporaryDirectory() as directory:
            (Path(directory) / "plugin_fixture.html").write_text("<p>Plugin: {{ example.message }}</p>")
            templates = deepcopy(settings.TEMPLATES)
            templates[0]["DIRS"] = [directory, *templates[0]["DIRS"]]
            with override_settings(TEMPLATES=templates), \
                 patch("notification.mails.UserNotification.objects.filter", return_value=[note(self.milestone, "sta", "Notice")]), \
                 patch("notification.mails.LMUserSetting.get_setting", side_effect=lambda key, **kwargs: "en" if key == "NOTIFCATION_REPORT_LANGUAGE" else True), \
                 patch("plugin.registry.registry.with_mixin", return_value=[Plugin]), \
                 patch("plugin.templatetags.plugin_tags.registry.with_mixin", return_value=[Plugin]):
                mail = NotificationMail()
                mail.generate_context(user=self.user.pk)
                self.assertEqual(mail.context["example"], {"message": "Plugin content"})
                self.assertEqual(len(mail.context["notification"]["endpoints_milestones"]), 1)
                html = mail.render_html(user=self.user.pk)
        self.assertIn("Notice", html)
        self.assertIn("Plugin: Plugin content", html)
