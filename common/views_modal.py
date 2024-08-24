
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import HttpResponse
from bootstrap_modal_forms.generic import BSModalCreateView, BSModalUpdateView, BSModalDeleteView, BSModalFormView
from django.utils.translation import gettext_lazy as _
from django.urls import reverse, reverse_lazy
from django.shortcuts import render
from . import models


from labsmanager.views_modal import BSmodalDeleteViwGenericForeingKeyMixin

class SubscriptionDeleteView(LoginRequiredMixin,BSmodalDeleteViwGenericForeingKeyMixin, BSModalDeleteView):
    model = models.subscription
    template_name = 'form_delete_base.html'
    success_url = reverse_lazy('employee')
    
    
class FavoriteDeleteView(LoginRequiredMixin,BSmodalDeleteViwGenericForeingKeyMixin, BSModalDeleteView):
    model = models.favorite
    template_name = 'form_delete_base.html'
    success_url = reverse_lazy('employee')    

### for password management with modal form ###
from .forms import ChangeLabPasswordForm
from django.contrib.auth import get_user_model
from django.contrib.auth import update_session_auth_hash

class ChangePasswordBSView(LoginRequiredMixin, BSModalFormView):
    model = get_user_model()
    template_name = 'account/change_password_form.html' #'form_base.html'
    form_class = ChangeLabPasswordForm
    success_message = _('Your password has been changed')
    success_url = '/'
    
    def post(self, request, *args, **kwargs):
        
        resp = super().post(request)

        form = self.get_form(self.form_class)
        if form.is_valid():
            form.save()
            update_session_auth_hash(request, form.user)
        return resp
    
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.model.objects.get(pk=self.request.user.pk)
        del kwargs['request']
        return kwargs
    
    def get_form(self, form_class=None):
        form =  super().get_form(form_class)
        user = self.model.objects.get(pk=self.request.user.pk)
        form.user = user
        return form
    
