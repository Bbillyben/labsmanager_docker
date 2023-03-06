from django.shortcuts import render
from django.http import HttpResponse

import os
from io import BytesIO
from django.http import FileResponse
from docxtpl import DocxTemplate
import jinja2

from labsmanager.settings import BASE_DIR
from staff.models import Employee,Employee_Status, GenericInfo
from expense.models import Contract
from project.models import Project, Participant
import datetime

def userReport(request, pk):
    
    template_path= os.path.join(BASE_DIR, 'templates/', 'reports/employee_report.docx')
    
    # context building
    context={'request': request,}
    context["current_date"]=datetime.datetime.utcnow()
    
    emp = Employee.objects.get(pk=pk)
    if not emp:
        return HttpResponse("not found", code=404)
    context["employee"]=emp
    
    info = GenericInfo.objects.filter(employee__pk=pk)
    context["info"]=info
    status = Employee_Status.objects.filter(employee__pk=pk)
    context["status"]=status
    
    contract = Contract.objects.filter(employee__pk=pk)
    context["contract"]=contract
    
    partProj = Participant.objects.filter(employee=emp)
    # project = Project.objects.filter(pk__in=partProj)
    context["project"]=partProj
    
    
    
    
    # rendering    
    doc = DocxTemplate(template_path)
    jinja_env = jinja2.Environment(autoescape=True)
    doc.render(context, autoescape=True)
    

    doc_io = BytesIO() # create a file-like object
    doc.save(doc_io) # save data to file-like object
    doc_io.seek(0) # go to the beginning of the file-like object

    response = HttpResponse(doc_io.read())

    # Content-Disposition header makes a file downloadable
    filename = "Employee_"+str(emp.first_name)+"_"+str(emp.last_name)+".docx"
    response["Content-Disposition"] = "attachment; filename="+filename

    # Set the appropriate Content-Type for docx file
    response["Content-Type"] = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"

    return response