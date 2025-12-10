from allauth.account.adapter import DefaultAccountAdapter
from django.conf import settings
from django.utils.http import url_has_allowed_host_and_scheme
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
        ## check wether there is a next_redir param in the login form,if so, redirect to that one
        next_url = request.GET.get("next_redir") or request.POST.get("next_redir")
        
        if next_url and len(next_url) > 1 and url_has_allowed_host_and_scheme(
            next_url,
            allowed_hosts={request.get_host()},
        ):
            return next_url
        
        ## redirect to the user param   
        redir_set = LMUserSetting.get_setting("REDIRECT_LOGGING", user = user)
        if redir_set == 'hub':
            return reverse('index')
        
        if redir_set== 'dashboard' and user.has_perm("common.display_dashboard"):
            return reverse('dashboard')
        
        if redir_set== 'calendar' and user.has_perm("common.display_calendar"):
            return reverse('calendar_main')
        
        if redir_set== 'employee':
            emp = Employee.objects.filter(user = user).first()
            if emp:
                return reverse('employee',kwargs={'pk': emp.pk})
        return reverse('index')
    
    def get_user_signed_up_signal(self):
        return user_signed_up
    
    def get_login_redirect_url(self, request):
        """"
        use to redirect user when logged in from his UserSetting REDIRECT_LOGGING (interface parameter)
        """
       
        return self.get_logged_redirect_url(request)
        
        
    
    def get_signup_redirect_url(self, request):
        return self.get_logged_redirect_url(request)