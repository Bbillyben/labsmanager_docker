from django.shortcuts import render
from django.http import HttpResponse, JsonResponse
from django.urls import reverse, reverse_lazy

from bootstrap_modal_forms.generic import BSModalFormView
from .models import EmployeeWordReport, EmployeePDFReport, ProjectWordReport, ProjectPDFReport
from .forms import ReportBaseForm, EmployeeWordReportForm, EmployeePDFReportForm, ProjectWordReportForm, ProjectPDFReportForm

class WordBaseReportView(BSModalFormView):
    template_name = 'form_base.html'
    form_class = ReportBaseForm
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
        
        form = self.get_form()
        if form.is_valid():
            self.form_valid(form)
        else:
            return self.form_invalid(form)
        
        
        
        template_id=request.POST.get("Template", None)
        emp_id=request.POST.get("pk", None)
        start=request.POST.get("start_date", None)
        end=request.POST.get("end_date", None)
    
        
        # self.success_url = reverse('employee_report', kwargs={'pk':emp_id, 'template':template_id,})
        urlP = reverse(self.nav_url, kwargs={'pk':emp_id, 'template':template_id,})
        urlP = request.build_absolute_uri(urlP)
        
        # build GET parameter from post data
        param=""
        for ke in request.POST:
            if ke != "Template" and ke!="pk" and ke!="csrfmiddlewaretoken":
                param=param+str(ke)+"="+request.POST.get(ke, None)+"&"
                
        urlP = "%s?%s" % (urlP, param)
                
        return  JsonResponse({'navigate':urlP})
    
    
class EmployeeWordReportView(WordBaseReportView):
    form_class = EmployeeWordReportForm
    nav_url='employee_report'

class EmployeePDFReportView(WordBaseReportView):
    form_class = EmployeePDFReportForm
    nav_url='employee_pdf_report'  

class ProjectWordReportView(WordBaseReportView):
    form_class = ProjectWordReportForm
    nav_url='project_report'

class ProjectPDFReportView(WordBaseReportView):
    form_class = ProjectPDFReportForm
    nav_url='project_pdf_report' 

def userWordReport(request, pk, template):
    rep = EmployeeWordReport.objects.get(pk=template)
    return rep.render(request, {"pk":int(pk),})

def userPDFReport(request, pk, template):
    rep = EmployeePDFReport.objects.get(pk=template)
    return rep.render(request, {"pk":int(pk),})

def projectWordReport(request, pk, template):
    rep = ProjectWordReport.objects.get(pk=template)
    return rep.render(request, {"pk":int(pk),})

def projectPDFReport(request, pk, template):
    rep = ProjectPDFReport.objects.get(pk=template)
    return rep.render(request, {"pk":int(pk),})

    
    