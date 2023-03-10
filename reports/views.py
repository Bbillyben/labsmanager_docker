from django.shortcuts import render
from django.http import HttpResponse, JsonResponse
from django.urls import reverse, reverse_lazy

from bootstrap_modal_forms.generic import BSModalFormView
from .models import EmployeeWordReport
from .forms import EmployeeWordReportForm

from django.http import HttpResponseRedirect
class EmployeeReportView(BSModalFormView):
    template_name = 'form_base.html'
    form_class = EmployeeWordReportForm
    success_url = reverse_lazy('employee_index')
    
    def get(self, request, *args, **kwargs):
        if 'pk' in kwargs:
            form = self.form_class(initial={'employee_pk': kwargs['pk']})
        else:
            form = self.form_class()
        
        context = {'form': form}
        return render(request, self.template_name , context)
    
    def post(self, request, *args, **kwargs):
        
        template_id=request.POST.get("Template", None)
        emp_id=request.POST.get("employee_pk", None)
        
        # self.success_url = reverse('employee_report', kwargs={'pk':emp_id, 'template':template_id,})
        urlP = reverse('employee_report', kwargs={'pk':emp_id, 'template':template_id,})
        urlP = request.build_absolute_uri(urlP)
        print("urlP :"+str(urlP))
        
        return  JsonResponse({'navigate':urlP})# super().post(request)

    

def userReport(request, pk, template):
    rep = EmployeeWordReport.objects.get(pk=template)
    return rep.render(request, {"pk":int(pk),})
    
    