from django.utils.translation import gettext_lazy as _
from django.contrib.auth import password_validation
from django import forms
from allauth.account.forms import ChangePasswordForm, PasswordField, ResetPasswordKeyForm, SignupForm
from allauth.account.adapter import get_adapter

class CheckPasswordField(PasswordField):
    def __init__(self, *args, **kwargs):
        kwargs["autocomplete"] = "new-password"
        super().__init__(*args, **kwargs)
        self.user = None

    def clean(self, value):
        value = super().clean(value)
        value = get_adapter().clean_password(value, user=self.user)
        return value

class ChangeLabPasswordForm(ChangePasswordForm):
    password1 = CheckPasswordField(label=_("New Password"))
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.hints = password_validation.password_validators_help_text_html()
        

class ResetLabPasswordKeyForm(ResetPasswordKeyForm):
    password1 = CheckPasswordField(label=_("New Password"))
    
    def __init__(self, *args, **kwargs):

        super(ResetLabPasswordKeyForm, self).__init__(*args, **kwargs)
        self.hints = password_validation.password_validators_help_text_html()

class LabSignupForm(SignupForm):
    def __init__(self, *args, **kwargs):
        super(LabSignupForm, self).__init__(*args, **kwargs)
        self.hints = password_validation.password_validators_help_text_html()
    # def save(self, request):
    #     user = super(CustomSignupForm, self).save(request)
    #     user.first_name = self.cleaned_data['first_name']
    #     user.last_name = self.cleaned_data['last_name']
    #     user.save()
    #     return user