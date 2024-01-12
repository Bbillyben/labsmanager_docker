from .models import OrganizationInfosType,ContactInfoType, ContactType, OrganizationInfos, Contact, ContactInfo
from django import forms
from labsmanager.mixin import CleanedDataFormMixin, IconFormMixin
from bootstrap_modal_forms.forms import BSModalModelForm, BSModalForm
from django.contrib.contenttypes.models import ContentType

class OrganizationInfosTypeForm(CleanedDataFormMixin, IconFormMixin, BSModalModelForm):

    class Meta:
        model = OrganizationInfosType
        fields = ['name', 'icon',]

class ContactInfoTypeForm(CleanedDataFormMixin, IconFormMixin,  BSModalModelForm):

    class Meta:
        model = ContactInfoType
        fields = ['name', 'icon',]

class ContactTypeForm(CleanedDataFormMixin, BSModalModelForm):

    class Meta:
        model = ContactType
        fields = ['name',]
    
class OrganizationInfosForm(CleanedDataFormMixin, BSModalModelForm):
    class Meta:
        model = OrganizationInfos
        fields = ['content_type', 'object_id', 'info', 'value','comment']
        
    def __init__(self, *args, **kwargs):
        if ('initial' in kwargs and 'obj_id' in kwargs['initial'] ):
            ct = ContentType.objects.get(app_label=kwargs['initial']['app'], model=kwargs['initial']['model'])
            self.base_fields['object_id'].initial=kwargs['initial']['obj_id']
            self.base_fields['content_type'].initial = ct.pk
        super().__init__(*args, **kwargs)
        self.fields['object_id'].widget = forms.HiddenInput()
        self.fields['content_type'].widget = forms.HiddenInput()

class ContactForm(CleanedDataFormMixin, BSModalModelForm):
    class Meta:
        model = Contact
        fields = ['content_type', 'object_id', 'first_name', 'last_name','type','comment']
        
    def __init__(self, *args, **kwargs):
        if ('initial' in kwargs and 'obj_id' in kwargs['initial'] ):
            ct = ContentType.objects.get(app_label=kwargs['initial']['app'], model=kwargs['initial']['model'])
            self.base_fields['object_id'].initial=kwargs['initial']['obj_id']
            self.base_fields['content_type'].initial = ct.pk
        super().__init__(*args, **kwargs)
        self.fields['object_id'].widget = forms.HiddenInput()
        self.fields['content_type'].widget = forms.HiddenInput()

class ContactInfoForm(CleanedDataFormMixin, BSModalModelForm):
    class Meta:
        model = ContactInfo
        fields = ['contact', 'info', 'value', 'comment',]
    
    def __init__(self, *args, **kwargs):
        if ('initial' in kwargs and 'contact' in kwargs['initial'] ):
            self.base_fields['contact'].initial = kwargs['initial']['contact']
        super().__init__(*args, **kwargs)
        self.fields['contact'].widget = forms.HiddenInput()
        # self.fields['content_type'].widget = forms.HiddenInput()