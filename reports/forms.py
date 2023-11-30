from django.utils.translation import gettext_lazy as _
from bootstrap_modal_forms.forms import BSModalForm
from django import forms
from .models import WordReport, EmployeeWordReport, ProjectWordReport, EmployeePDFReport, ProjectPDFReport
from labsmanager.forms import DateInput
from datetime import date
from dateutil.relativedelta import relativedelta

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
    
class DateReportBaseForm(BSModalForm):
    start_date = forms.DateField(widget=DateInput(), required=False,)
    end_date = forms.DateField(widget=DateInput(), required=False,)
    
    class Meta:
            fields = ['start_date','end_date',]
    
    def __init__(self, *args, **kwargs):
        
        self.base_fields['start_date'].initial = date.today() - relativedelta(years=1)
        self.base_fields['end_date'].initial = date.today()
        super().__init__(*args, **kwargs)

    def clean_end_date(self, *args, **kwargs):
        if self.cleaned_data['start_date'] == None :
            return self.cleaned_data['end_date']
        if self.cleaned_data['end_date'] != None and self.cleaned_data['start_date'] > self.cleaned_data['end_date']:
            raise forms.ValidationError(_('End Date (%s) should be later than start date (%s) ') % (self.cleaned_data['end_date'], self.cleaned_data['start_date']))
        return self.cleaned_data['end_date']
    

class EmployeeWordReportForm(DateReportBaseForm, ReportBaseForm):
    
    class Meta:
        model = EmployeeWordReport

class EmployeePDFReportForm(DateReportBaseForm, ReportBaseForm):
    class Meta:
        model = EmployeePDFReport
 
class ProjectWordReportForm(ReportBaseForm):
    class Meta:
        model = ProjectWordReport
        
class ProjectPDFReportForm(ReportBaseForm):
    class Meta:
        model = ProjectPDFReport