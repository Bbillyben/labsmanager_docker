from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.http import JsonResponse
from rest_framework.test import APITestCase


SEND = "/api/v1/settings/notifications/test-email/send/"
PREVIEW = "/api/v1/settings/notifications/test-email/preview/"


class NotificationTestV1Tests(APITestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username="notification-test")
        self.other = get_user_model().objects.create_user(username="notification-other")

    def test_authenticated_session_is_required(self):
        self.assertIn(self.client.post(SEND).status_code, (401, 403))
        self.assertIn(self.client.post(PREVIEW).status_code, (401, 403))

    @patch("settings.user_api_v1.send_notification")
    def test_send_uses_only_request_user_and_adapts_legacy_response(self, send):
        self.client.force_login(self.user)
        send.return_value = JsonResponse({"status": "success", "message": "Mail Send"})
        result = self.client.post(SEND, {"user": self.other.pk}, format="json")
        self.assertEqual(result.status_code, 200)
        self.assertEqual(result.data, {"sent": True})
        send.assert_called_once_with(user_pk=self.user.pk)

        send.return_value = JsonResponse({"status": "error", "message": "No verified primary email"}, status=400)
        result = self.client.post(SEND, format="json")
        self.assertEqual(result.status_code, 400)
        self.assertEqual(result.data["detail"], "No verified primary email")
        send.side_effect = RuntimeError("mail failed")
        self.assertEqual(self.client.post(SEND).status_code, 500)

    @patch("settings.user_api_v1.SubscriptionMail")
    def test_preview_returns_html_for_current_user_without_sending(self, mail_class):
        self.client.force_login(self.user)
        mail = mail_class.return_value
        mail.render_html.return_value = "<html><body>Test mail</body></html>"
        result = self.client.post(PREVIEW, {"user": self.other.pk}, format="json")
        self.assertEqual(result.status_code, 200)
        self.assertTrue(result["Content-Type"].startswith("text/html"))
        self.assertEqual(result.content.decode(), "<html><body>Test mail</body></html>")
        mail.generate_context.assert_called_once_with(user=self.user, embedImg=True)
        mail.render_html.assert_called_once_with(user=self.user, embedImg=True)
        mail.send.assert_not_called()

        mail.render_html.side_effect = RuntimeError("render failed")
        result = self.client.post(PREVIEW)
        self.assertEqual(result.status_code, 500)
        self.assertIn("detail", result.data)
