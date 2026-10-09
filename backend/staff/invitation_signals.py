from allauth.account.signals import user_signed_up
from django.dispatch import receiver

from .invitation_provisioning import apply_provisioning_for_signup


@receiver(user_signed_up, dispatch_uid="staff.apply_invitation_provisioning")
def provision_invited_user(sender, request, user, **kwargs):
    apply_provisioning_for_signup(user)
