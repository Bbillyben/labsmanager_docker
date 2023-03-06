from django.contrib.auth.models import User
from django.contrib.auth.backends import ModelBackend

class MailAutenticateBackend(ModelBackend):
    """
    This is a ModelBacked that allows authentication with either a username or an email address.

    """
    def authenticate(self, request, **kwargs):
        
        if 'username' in kwargs:
            username=kwargs["username"]
        else:
            return None
        
        if 'password' in kwargs:
            password=kwargs["password"]
        else:
            return None
        
        if '@' in username:
            kwargs = {'email': username}
        else:
            kwargs = {'username': username}
        try:
            user = User.objects.get(**kwargs)
            if user.check_password(password):
                return user
        except User.DoesNotExist:
            return None

    def get_user(self, username):
        try:
            return User.objects.get(pk=username)
        except User.DoesNotExist:
            return None