from django.contrib.auth.mixins import LoginRequiredMixin
from bootstrap_modal_forms.generic import BSModalCreateView, BSModalUpdateView, BSModalDeleteView, BSModalFormView
from django.utils.translation import gettext_lazy as _
from django.urls import reverse, reverse_lazy

from labsmanager.views_modal import BSmodalDeleteViwGenericForeingKeyMixin

from . import forms, models

class OrganizationInfosTypeFormCreateView(LoginRequiredMixin, BSModalCreateView):
    template_name = 'form_base.html'
    form_class = forms.OrganizationInfosTypeForm
    success_message = 'Success: Project was updated.'
    success_url = reverse_lazy('project_index')
    label_confirm = "Confirm"
    model = models.OrganizationInfosType
    
    
class OrganizationInfosTypeFormUpdateView(LoginRequiredMixin, BSModalUpdateView):
    model = models.OrganizationInfosType    
    template_name = 'form_validate_base.html'
    form_class = forms.OrganizationInfosTypeForm
    success_message = 'Success: Leave was updated.'
    success_url = reverse_lazy('project_index')
    label_confirm = "Confirm"
    
class ContactInfoTypeFormCreateView(LoginRequiredMixin, BSModalCreateView):
    template_name = 'form_base.html'
    form_class = forms.ContactInfoTypeForm
    success_message = 'Success: Project was updated.'
    success_url = reverse_lazy('project_index')
    label_confirm = "Confirm"
    model = models.ContactInfoType
    
    
class ContactInfoTypeFormUpdateView(LoginRequiredMixin, BSModalUpdateView):
    model = models.ContactInfoType    
    template_name = 'form_validate_base.html'
    form_class = forms.ContactInfoTypeForm
    success_message = 'Success: Leave was updated.'
    success_url = reverse_lazy('project_index')
    label_confirm = "Confirm"
    
    
    
    
class ContactTypeFormCreateView(LoginRequiredMixin, BSModalCreateView):
    template_name = 'form_base.html'
    form_class = forms.ContactTypeForm
    success_message = 'Success: Project was updated.'
    success_url = reverse_lazy('project_index')
    label_confirm = "Confirm"
    model = models.ContactInfoType
    
    
class ContactTypeFormUpdateView(LoginRequiredMixin, BSModalUpdateView):
    model = models.ContactType    
    template_name = 'form_validate_base.html'
    form_class = forms.ContactTypeForm
    success_message = 'Success: Leave was updated.'
    success_url = reverse_lazy('project_index')
    label_confirm = "Confirm"


class ContactCreateView(LoginRequiredMixin, BSModalCreateView):
    template_name = 'form_base.html'
    form_class = forms.ContactForm
    success_message = 'Success: Project was updated.'
    success_url = reverse_lazy('project_index')
    label_confirm = "Confirm"
    model = models.Contact
    
    def get(self, request, *args, **kwargs):
        kw = self.get_form_kwargs()
        initial={}
        if 'obj_id' in kwargs and 'app' in kwargs and 'model' in kwargs:
            initial={
                'app':kwargs['app'],
                'model':kwargs['model'],
                'obj_id':kwargs['obj_id'],
            }
            
        kw['initial'] = initial
        form = self.form_class(**kw)
        return super().get(request)
    
class ContactUpdateView(LoginRequiredMixin, BSModalUpdateView):
    model = models.Contact    
    template_name = 'form_validate_base.html'
    form_class = forms.ContactForm
    success_message = 'Success: Leave was updated.'
    success_url = reverse_lazy('project_index')
    label_confirm = "Confirm"



class ContactRemoveView(LoginRequiredMixin, BSmodalDeleteViwGenericForeingKeyMixin, BSModalDeleteView):
    model = models.Contact
    template_name = 'form_delete_base.html'
    success_url = reverse_lazy('project_index')  
    
    


class ContactInfoCreateView(LoginRequiredMixin, BSModalCreateView):
    template_name = 'form_base.html'
    form_class = forms.ContactInfoForm
    success_message = 'Success: Project was updated.'
    success_url = reverse_lazy('project_index')
    label_confirm = "Confirm"
    model = models.ContactInfo
    
    def get(self, request, *args, **kwargs):
        kw = self.get_form_kwargs()
        initial={}
        if 'id' in kwargs:
            initial={
                'contact':kwargs['id'],
            }
            
        kw['initial'] = initial
        form = self.form_class(**kw)
        return super().get(request)
    
class ContactInfoUpdateView(LoginRequiredMixin, BSModalUpdateView):
    model = models.ContactInfo    
    template_name = 'form_validate_base.html'
    form_class = forms.ContactInfoForm
    success_message = 'Success: Leave was updated.'
    success_url = reverse_lazy('project_index')
    label_confirm = "Confirm"   

class ContactInfoRemoveView(LoginRequiredMixin, BSModalDeleteView):
    model = models.ContactInfo
    template_name = 'form_delete_base.html'
    success_url = reverse_lazy('project_index')     

         
class OrganizationInfosCreateView(LoginRequiredMixin, BSModalCreateView):
    template_name = 'form_base.html'
    form_class = forms.OrganizationInfosForm
    success_message = 'Success: Project was updated.'
    success_url = reverse_lazy('project_index')
    label_confirm = "Confirm"
    model = models.ContactInfoType
    
    def get(self, request, *args, **kwargs):
        kw = self.get_form_kwargs()
        initial={}
        if 'obj_id' in kwargs and 'app' in kwargs and 'model' in kwargs:
            initial={
                'app':kwargs['app'],
                'model':kwargs['model'],
                'obj_id':kwargs['obj_id'],
            }
            
        kw['initial'] = initial
        form = self.form_class(**kw)
        return super().get(request)
    
    
class OrganizationInfosUpdateView(LoginRequiredMixin, BSModalUpdateView):
    model = models.OrganizationInfos    
    template_name = 'form_validate_base.html'
    form_class = forms.OrganizationInfosForm
    success_message = 'Success: Leave was updated.'
    success_url = reverse_lazy('project_index')
    label_confirm = "Confirm"
    
class OrganizationInfosRemoveView(LoginRequiredMixin, BSModalDeleteView):
    model = models.OrganizationInfos
    template_name = 'form_delete_base.html'
    success_url = reverse_lazy('project_index')
    
    
class GenericNoteCreateView(LoginRequiredMixin, BSModalCreateView):
    template_name = 'form_base.html'
    form_class = forms.GenericNoteForm
    success_message = 'Success: Note was created.'
    success_url = reverse_lazy('project_index')
    label_confirm = "Confirm"
    model = models.GenericNote
    
    def get(self, request, *args, **kwargs):
        kw = self.get_form_kwargs()
        initial={}
        if 'obj_id' in kwargs and 'app' in kwargs and 'model' in kwargs:
            initial={
                'app':kwargs['app'],
                'model':kwargs['model'],
                'obj_id':kwargs['obj_id'],
            }
            
        kw['initial'] = initial
        form = self.form_class(**kw)
        return super().get(request)

class GenericNoteUpdateView(LoginRequiredMixin, BSModalUpdateView):
    model = models.GenericNote    
    template_name = 'form_validate_base.html'
    form_class = forms.GenericNoteForm
    success_message = 'Success: Leave was updated.'
    success_url = reverse_lazy('project_index')
    label_confirm = "Confirm"
    
class GenericNoteRemoveView(LoginRequiredMixin, BSmodalDeleteViwGenericForeingKeyMixin, BSModalDeleteView):
    model = models.GenericNote
    template_name = 'form_delete_base.html'
    success_url = reverse_lazy('employee_index')
    success_message = "deleted"