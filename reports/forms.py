from bootstrap_modal_forms.forms import BSModalForm
from django import forms
from .models import WordReport, EmployeeWordReport, ProjectWordReport, EmployeePDFReport, ProjectPDFReport

class ReportBaseForm(BSModalForm):
    class Meta:
        fields = ['Template','pk',]
        #abstract = True
        model = WordReport
        
    Template = forms.ModelChoiceField(None)
    pk = forms.IntegerField(widget=forms.HiddenInput)
    
    def get_queryset(self):
        qset = self.Meta.model.objects.all()
        return qset
    
    def __init__(self, *args, **kwargs):
        qset= self.get_queryset()
        if qset.count()>0:
            self.base_fields['Template'] = forms.ModelChoiceField(qset, initial=qset.first())
        else:
             self.base_fields['Template'] = forms.ModelChoiceField(qset)
        super().__init__(*args, **kwargs)
    
    
class EmployeeWordReportForm(ReportBaseForm):
    class Meta:
        model = EmployeeWordReport

class EmployeePDFReportForm(ReportBaseForm):
    class Meta:
        model = EmployeePDFReport
 
class ProjectWordReportForm(ReportBaseForm):
    class Meta:
        model = ProjectWordReport
        
class ProjectPDFReportForm(ReportBaseForm):
    class Meta:
        model = ProjectPDFReport