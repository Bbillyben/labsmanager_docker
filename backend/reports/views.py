from django.shortcuts import get_object_or_404, render
from django.http import FileResponse, Http404, HttpResponse, HttpResponseBadRequest, JsonResponse
from django.urls import reverse, reverse_lazy
from django.contrib.auth.decorators import login_required
from django.apps import apps

from bootstrap_modal_forms.generic import BSModalFormView
from .models import EmployeeWordReport, EmployeePDFReport, ProjectWordReport, ProjectPDFReport, TemplateReport
from .forms import ReportBaseForm, EmployeeWordReportForm, EmployeePDFReportForm, ProjectWordReportForm, ProjectPDFReportForm
from .api_v1 import scoped_report, validate_legacy_employee_dates

import logging
logger =logging.getLogger("labsmanager")

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
        logger.debug(f"WordBaseReportView-post / urlP : {urlP}")
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

@login_required
def userWordReport(request, pk, template):
    return render_legacy_report(request, pk, template, "employee", "word")

@login_required
def userPDFReport(request, pk, template):
    return render_legacy_report(request, pk, template, "employee", "pdf")

@login_required
def projectWordReport(request, pk, template):
    return render_legacy_report(request, pk, template, "project", "word")

@login_required
def projectPDFReport(request, pk, template):
    return render_legacy_report(request, pk, template, "project", "pdf")

    
def render_legacy_report(request, pk, template, entity, format_name):
    report_model, instance = scoped_report(request.user, entity, pk, format_name)
    if entity == "employee" and not validate_legacy_employee_dates(request):
        return HttpResponseBadRequest("Invalid report date range.")
    report = get_object_or_404(report_model, pk=template)
    return report.render(request, {"pk": instance.pk})

@login_required
def download_template_report(request, app, model, pk):
    templateModel = apps.get_model(app_label=app, model_name=model)
    report = get_object_or_404(templateModel, pk=pk)
    if not report.template:
        raise Http404("Aucun fichier n'est associé à ce rapport.")
    response = FileResponse(report.template.open('rb'), as_attachment=True, filename=report.template.name)
    return response
