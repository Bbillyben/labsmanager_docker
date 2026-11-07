"""Forms for Equipment reference lists managed from user settings."""

from django import forms

from .models import EquipmentCategory, EquipmentGenericInfoType


class EquipmentCategoryListForm(forms.ModelForm):
    is_active = forms.BooleanField(label=EquipmentCategory._meta.get_field("is_active").verbose_name,
                                   initial=True, required=False)

    class Meta:
        model = EquipmentCategory
        fields = ("name", "is_active")

    def __init__(self, *args, **kwargs):
        kwargs.pop("request", None)
        super().__init__(*args, **kwargs)


class EquipmentInfoTypeListForm(forms.ModelForm):
    class Meta:
        model = EquipmentGenericInfoType
        fields = ("name", "icon")

    def __init__(self, *args, **kwargs):
        kwargs.pop("request", None)
        super().__init__(*args, **kwargs)
