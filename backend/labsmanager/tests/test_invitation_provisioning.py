"""Focused Employee/Group assignments through the existing invitation flows."""

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group, Permission
from django.urls import reverse
from django.core import mail
from django.test import override_settings
from django.utils import timezone
from invitations.models import Invitation
from rest_framework.test import APITestCase

from staff.models import Employee, InvitationProvisioning


@override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend", REACT_PUBLIC_URL="http://frontend.example/app")
class InvitationProvisioningTests(APITestCase):
    admin_url = "/api/v1/settings/admin/invitations/"
    bridge_url = "/api/v1/auth/invitations/bridge/"
    signup_url = "/api/v1/auth/invitations/current/"

    def setUp(self):
        self.admin = get_user_model().objects.create_superuser("admin-provisioning", "admin@example.test", "password")
        self.staff = get_user_model().objects.create_user("staff-provisioning", is_staff=True)
        self.employee = Employee.objects.create(first_name="Ada", last_name="Test", email="invited@example.test")
        self.group = Group.objects.create(name="Lab readers")
        self.group.permissions.add(Permission.objects.get(content_type__app_label="staff", codename="view_employee"))

    def invite(self, *, email="invited@example.test", employee=None, groups=None, actor=None):
        self.client.force_login(actor or self.admin)
        response = self.client.post(self.admin_url, {
            "email": email,
            "employee_id": employee.pk if employee else None,
            "group_ids": [group.pk for group in (groups or [])],
        }, format="json")
        self.assertEqual(response.status_code, 201, response.data)
        self.client.logout()
        return Invitation.objects.get(email=email)

    def signup(self, invitation, *, username="invited-person", employee_id=None):
        self.assertEqual(self.client.post(self.bridge_url, {"token": invitation.key}, format="json").status_code, 200)
        payload = {"username": username, "password1": "Invited-password-123!", "password2": "Invited-password-123!"}
        if employee_id is not None:
            payload["employee_id"] = employee_id
        return self.client.post(self.signup_url, payload, format="json")

    def test_employee_and_groups_are_applied_before_first_me_response(self):
        invitation = self.invite(employee=self.employee, groups=[self.group])
        provisioning = InvitationProvisioning.objects.get(invitation=invitation)
        self.assertEqual(provisioning.employee_id, self.employee.pk)
        self.assertEqual(list(provisioning.groups.all()), [self.group])
        result = self.signup(invitation, employee_id=999999)
        self.assertEqual(result.status_code, 200, result.data)
        user = get_user_model().objects.get(username="invited-person")
        self.employee.refresh_from_db()
        invitation.refresh_from_db()
        self.assertEqual(self.employee.user_id, user.pk)
        self.assertTrue(user.groups.filter(pk=self.group.pk).exists())
        self.assertTrue(invitation.accepted)
        me = self.client.get("/api/v1/me/")
        self.assertEqual(me.status_code, 200)
        self.assertEqual(me.data["employee"]["id"], self.employee.pk)
        self.assertTrue(me.data["capabilities"]["view_employee_list"])
        self.assertEqual(self.client.post(self.bridge_url, {"token": invitation.key}, format="json").status_code, 409)

    def test_employee_only_and_groups_only_work(self):
        employee_invite = self.invite(employee=self.employee)
        self.assertEqual(self.signup(employee_invite).status_code, 200)
        self.employee.refresh_from_db()
        self.assertIsNotNone(self.employee.user_id)
        self.assertFalse(get_user_model().objects.get(pk=self.employee.user_id).groups.exists())
        self.client.logout()
        group_invite = self.invite(email="group-only@example.test", groups=[self.group])
        self.assertEqual(self.signup(group_invite, username="group-only").status_code, 200)
        self.assertTrue(get_user_model().objects.get(username="group-only").groups.filter(pk=self.group.pk).exists())

    def test_missing_provisioning_and_deletion_keep_historical_behavior(self):
        invitation = Invitation.create("plain@example.test")
        invitation.sent = timezone.now()
        invitation.save()
        self.assertEqual(self.signup(invitation).status_code, 200)
        self.assertFalse(Employee.objects.filter(user__username="invited-person").exists())
        self.client.logout()
        invitation2 = self.invite(email="delete@example.test", groups=[self.group])
        invitation2.delete()
        self.assertFalse(InvitationProvisioning.objects.filter(invitation_id=invitation2.pk).exists())

    def test_employee_linked_after_invite_refuses_signup_without_creating_user(self):
        invitation = self.invite(employee=self.employee, groups=[self.group])
        other = get_user_model().objects.create_user("already-linked")
        self.employee.user = other
        self.employee.save(update_fields=["user"])
        result = self.signup(invitation)
        self.assertEqual(result.status_code, 409)
        self.assertEqual(self.employee.user_id, other.pk)
        self.assertFalse(get_user_model().objects.filter(username="invited-person").exists())
        invitation.refresh_from_db()
        self.assertFalse(invitation.accepted)

    def test_second_invitation_cannot_reuse_employee(self):
        self.employee.email = None
        self.employee.save(update_fields=["email"])
        first = self.invite(employee=self.employee)
        second = self.invite(email="another@example.test", employee=self.employee)
        self.assertEqual(self.signup(first).status_code, 200)
        self.client.logout()
        self.assertEqual(self.signup(second, username="second-invite").status_code, 409)
        self.assertFalse(get_user_model().objects.filter(username="second-invite").exists())

    def test_group_assignment_requires_superuser_and_email_must_match(self):
        self.client.force_login(self.staff)
        self.assertEqual(self.client.post(self.admin_url, {"email": "staff@example.test", "group_ids": [self.group.pk]}, format="json").status_code, 400)
        self.assertFalse(Invitation.objects.filter(email="staff@example.test").exists())
        self.assertEqual(self.client.post(self.admin_url, {"email": "staff@example.test"}, format="json").status_code, 201)
        self.assertEqual(self.client.patch(f"{self.admin_url}{Invitation.objects.get(email='staff@example.test').pk}/", {"group_ids": []}, format="json").status_code, 400)
        self.client.force_login(self.admin)
        self.assertEqual(self.client.post(self.admin_url, {"email": "different@example.test", "employee_id": self.employee.pk}, format="json").status_code, 400)
        self.assertFalse(Invitation.objects.filter(email="different@example.test").exists())

    def test_pending_assignments_can_change_and_invitee_never_sees_them(self):
        invitation = self.invite()
        self.client.force_login(self.admin)
        response = self.client.patch(f"{self.admin_url}{invitation.pk}/", {"employee_id": self.employee.pk, "group_ids": [self.group.pk]}, format="json")
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(response.data["employee"]["id"], self.employee.pk)
        self.client.logout()
        bridge = self.client.post(self.bridge_url, {"token": invitation.key}, format="json")
        self.assertEqual(bridge.status_code, 200)
        self.assertNotIn("employee", bridge.data)
        self.assertNotIn("groups", bridge.data)
        self.assertNotIn("group_ids", bridge.data)
        self.assertEqual(self.client.get(self.signup_url).status_code, 200)

    def test_new_invitation_still_sends_react_email(self):
        invitation = self.invite(employee=self.employee)
        self.assertIn(f"/app/invitations/accept/{invitation.key}/", mail.outbox[-1].body)

    def test_django_admin_add_form_saves_assignments_before_sending(self):
        self.client.force_login(self.admin)
        url = reverse("admin:invitations_invitation_add")
        page = self.client.get(url)
        self.assertEqual(page.status_code, 200)
        self.assertContains(page, 'name="employee"')
        self.assertContains(page, 'name="groups"')
        response = self.client.post(url, {
            "email": "invited@example.test", "inviter": self.admin.pk,
            "employee": self.employee.pk, "groups": [self.group.pk], "_save": "Save",
        })
        self.assertEqual(response.status_code, 302, response.context)
        invitation = Invitation.objects.get(email="invited@example.test")
        provisioning = InvitationProvisioning.objects.get(invitation=invitation)
        self.assertEqual(provisioning.employee_id, self.employee.pk)
        self.assertTrue(provisioning.groups.filter(pk=self.group.pk).exists())
        self.assertIn(f"/app/invitations/accept/{invitation.key}/", mail.outbox[-1].body)

    def test_legacy_signup_applies_assignments_and_rolls_back_employee_conflict(self):
        invitation = self.invite(employee=self.employee, groups=[self.group])
        self.assertEqual(self.client.get(f"/invitations/accept/{invitation.key}/").status_code, 302)
        signup_data = {"email": invitation.email, "username": "legacy-invited", "password1": "Invited-password-123!", "password2": "Invited-password-123!"}
        response = self.client.post("/accounts/signup/", signup_data)
        self.assertEqual(response.status_code, 302)
        self.employee.refresh_from_db()
        self.assertEqual(self.employee.user.username, "legacy-invited")
        self.assertTrue(self.employee.user.groups.filter(pk=self.group.pk).exists())
        self.client.logout()
        second = self.invite(email="second@example.test")
        InvitationProvisioning.objects.create(invitation=second, employee=self.employee)
        self.client.get(f"/invitations/accept/{second.key}/")
        signup_data["email"] = second.email
        signup_data["username"] = "should-not-exist"
        refused = self.client.post("/accounts/signup/", signup_data)
        self.assertEqual(refused.status_code, 200)
        self.assertFalse(get_user_model().objects.filter(username="should-not-exist").exists())
        second.refresh_from_db()
        self.assertFalse(second.accepted)
