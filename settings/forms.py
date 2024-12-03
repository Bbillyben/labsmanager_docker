from django import forms
from django.utils.translation import gettext_lazy as _
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError

from bootstrap_modal_forms.forms import BSModalModelForm
from invitations.forms import InviteForm, CleanEmailMixin
from invitations.models import Invitation

from invitations.exceptions import AlreadyAccepted, AlreadyInvited, UserRegisteredEmail
from invitations.adapters import get_invitations_adapter
from labsmanager.utils import is_ajax

class labInviteForm(InviteForm, BSModalModelForm):
    class Meta:
        model = Invitation
        fields = ['email',]
    
    # def save(self, *args, **kwargs):
    #     print("############################# labInviteForm - save called")
    #     print(f' self.request.META is ajax {is_ajax(self.request.META)}')
    #     return super(labInviteForm).save(*args, **kwargs)