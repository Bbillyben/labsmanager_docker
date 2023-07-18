
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import HttpResponse
from bootstrap_modal_forms.generic import BSModalCreateView, BSModalUpdateView, BSModalDeleteView, BSModalFormView
from django.utils.translation import gettext_lazy as _
from django.urls import reverse, reverse_lazy
from django.shortcuts import render
from . import models




class SubscriptionDeleteView(LoginRequiredMixin, BSModalDeleteView):
    model = models.subscription
    template_name = 'form_delete_base.html'
    success_url = reverse_lazy('employee')
    
    def get_success_url(self):
        previous = self.request.META.get('HTTP_REFERER')
        return previous
        
    def post(self, *args, **kwargs):
        
        self.object = self.get_object()
        self.object.delete()
        return HttpResponse("okok", status=200)
    
class FavoriteDeleteView(LoginRequiredMixin, BSModalDeleteView):
    model = models.favorite
    template_name = 'form_delete_base.html'
    success_url = reverse_lazy('employee')
    
    def get_success_url(self):
        previous = self.request.META.get('HTTP_REFERER')
        return previous
        
    def post(self, *args, **kwargs):
        
        self.object = self.get_object()
        self.object.delete()
        return HttpResponse("okok", status=200)
    

### for password management with modal form ###
from allauth.account.forms import ChangePasswordForm
from django.contrib.auth import get_user_model
from django.contrib.auth import update_session_auth_hash

class ChangePasswordBSView(LoginRequiredMixin, BSModalFormView):
    model = get_user_model()
    template_name = 'form_base.html'
    form_class = ChangePasswordForm
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
    
