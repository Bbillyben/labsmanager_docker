from django.utils.translation import gettext_lazy as _
from django.contrib.auth import password_validation
from allauth.account.forms import ChangePasswordForm, PasswordField, ResetPasswordKeyForm
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
        print("[ResetLabPasswordKeyForm] -------------------------------------------------")
        print("Args :")
        for a in args:
            print(f'    - {a}')
        print("Kwargs : ")
        for k,v in kwargs.items():
            print(f'    - {k}:{v}')
        super(ResetLabPasswordKeyForm, self).__init__(*args, **kwargs)
        self.hints = password_validation.password_validators_help_text_html()