from bootstrap_modal_forms.forms import BSModalForm
from django import forms
from .models import EmployeeWordReport


class EmployeeWordReportForm(BSModalForm):
    class Meta:
        fields = ['Template','employee_pk',]
    
    queryset = EmployeeWordReport.objects.all()
    Template = forms.ModelChoiceField(queryset)
    employee_pk = forms.IntegerField(widget=forms.HiddenInput)
    
    def __init__(self, *args, **kwargs):
        
        print("[EmployeeWordReportForm] INIT")
        print("  - args:"+str(args))
        print("  - kwargs:"+str(kwargs))
        print("  - self.queryset.count:"+str(self.queryset.count()))
        if self.queryset.count()>0:
            print("okok")
            self.base_fields['Template'] = forms.ModelChoiceField(self.queryset, initial=self.queryset.first())
        else:
             self.base_fields['Template'] = forms.ModelChoiceField(self.queryset)
        super().__init__(*args, **kwargs)
    
    # def submit(self, request, *args, **kwargs):
    #     print("[EmployeeWordReportForm] submit ")
    #     print("  - args:"+str(args))
    #     print("  - kwargs:"+str(kwargs)) 
    #     super().post(request)