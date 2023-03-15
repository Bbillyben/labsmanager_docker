from django.shortcuts import render
from django.http import HttpResponse, JsonResponse
from django.urls import reverse, reverse_lazy

from bootstrap_modal_forms.generic import BSModalFormView
from .models import EmployeeWordReport, ProjectWordReport
from .forms import WordReportBaseForm, EmployeeWordReportForm, ProjectWordReportForm

class WordBaseReportView(BSModalFormView):
    template_name = 'form_base.html'
    form_class = WordReportBaseForm
    nav_url='to_be_defined'
    success_url = reverse_lazy('employee_index')
    
    def get(self, request, *args, **kwargs):
        if 'pk' in kwargs:
            form = self.form_class(initial={'pk': kwargs['pk']})
        else:
            form = self.form_class()
        
        context = {'form': form}
        return render(request, self.template_name , context)
    
    def post(self, request, *args, **kwargs):
        
        template_id=request.POST.get("Template", None)
        emp_id=request.POST.get("pk", None)
        
        # self.success_url = reverse('employee_report', kwargs={'pk':emp_id, 'template':template_id,})
        urlP = reverse(self.nav_url, kwargs={'pk':emp_id, 'template':template_id,})
        urlP = request.build_absolute_uri(urlP)
                
        return  JsonResponse({'navigate':urlP})
    
    
class EmployeeReportView(WordBaseReportView):
    form_class = EmployeeWordReportForm
    nav_url='employee_report'
    

class ProjectReportView(WordBaseReportView):
    form_class = ProjectWordReportForm
    nav_url='project_report'
    

def userReport(request, pk, template):
    rep = EmployeeWordReport.objects.get(pk=template)
    return rep.render(request, {"pk":int(pk),})

def projectReport(request, pk, template):
    rep = ProjectWordReport.objects.get(pk=template)
    return rep.render(request, {"pk":int(pk),})
    
    