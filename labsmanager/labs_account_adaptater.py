from allauth.account.adapter import DefaultAccountAdapter
from django.conf import settings
from allauth.account.signals import user_signed_up
from settings.models import LMUserSetting
from django.urls import reverse
from staff.models import Employee

class LabsManagerAccountAdapter(DefaultAccountAdapter):

    def is_open_for_signup(self, request):
        """
        Checks whether or not the site is open for signups.

        Next to simply returning True/False you can also intervene the
        regular flow by raising an ImmediateHttpResponse

        (Comment reproduced from the overridden method.)
        """
        if hasattr(request, "session") and request.session.get(
                    "account_verified_email",
                ):
                    return True
        if settings.ACCOUNT_ALLOW_SINGUP == True:
            return True
        else:
            return False
        
    def get_logged_redirect_url(self, request):
        user = request.user
        redir_set = LMUserSetting.get_setting("REDIRECT_LOGGING", user = user)
        url_redir = reverse('index')
        if redir_set == 'hub':
            url_redir = reverse('index')
        
        if redir_set== 'dashboard' and user.has_perm("common.display_dashboard"):
            url_redir = reverse('dashboard')
        
        if redir_set== 'calendar' and user.has_perm("common.display_calendar"):
            url_redir = reverse('calendar_main')
        
        if redir_set== 'employee':
            emp = Employee.objects.filter(user = user).first()
            if emp:
                url_redir = reverse('employee',kwargs={'pk': emp.pk})
        return url_redir
    
    def get_user_signed_up_signal(self):
        return user_signed_up
    
    def get_login_redirect_url(self, request):
        """"
        use to redirect user when logged in from his UserSetting REDIRECT_LOGGING (interface parameter)
        """
       
        return self.get_logged_redirect_url(request)
        
        
    
    def get_signup_redirect_url(self, request):
        return self.get_logged_redirect_url(request)