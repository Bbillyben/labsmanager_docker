from bootstrap_modal_forms.forms import BSModalForm
from django import forms
from .models import WordReport, EmployeeWordReport, ProjectWordReport

class WordReportBaseForm(BSModalForm):
    class Meta:
        fields = ['Template','pk',]
        #abstract = True
        model = WordReport
        
    Template = forms.ModelChoiceField(None)
    pk = forms.IntegerField(widget=forms.HiddenInput)
    
    def get_queryset(self):
        print("[WordReportBaseForm] - get_queryset :")
        qset = self.Meta.model.objects.all()
        return qset
    
    def __init__(self, *args, **kwargs):
        print("[WordReportBaseForm] - init :")
        qset= self.get_queryset()
        print(" set : "+str(qset))
        if qset.count()>0:
            self.base_fields['Template'] = forms.ModelChoiceField(qset, initial=qset.first())
        else:
             self.base_fields['Template'] = forms.ModelChoiceField(qset)
        super().__init__(*args, **kwargs)
    
    
class EmployeeWordReportForm(WordReportBaseForm):
    class Meta:
        model = EmployeeWordReport
    
 
class ProjectWordReportForm(WordReportBaseForm):
    class Meta:
        model = ProjectWordReport