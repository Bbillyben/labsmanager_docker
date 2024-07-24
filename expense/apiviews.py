from django.http import JsonResponse, HttpResponse
from django.db.models import Q, Value, Count, F, CharField, Max, Sum, Case, When, BooleanField
from django.db.models.functions import Concat
from django.shortcuts import render

from rest_framework import viewsets, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from django_filters import rest_framework as filters
from labsmanager import serializers  # UserSerializer, GroupSerializer, EmployeeSerialize, EmployeeStatusSerialize, ContractEmployeeSerializer, TeamSerializer, ParticipantSerializer, ProjectSerializer
from expense.models import Expense_point, Contract, Contract_expense
from .resources import ContractResource
from labsmanager.helpers import DownloadFile

from labsmanager.utils import str2bool
from staff.filters import EmployeeFilter
from expense.filters import ContractFilter
from project.models import Project
from fund.models import Fund, Fund_Item
from dashboard.utils import getDashboardContractTimeSlot

from staff.models import Employee
from django.core.exceptions import ObjectDoesNotExist

from datetime import datetime

from project.views import get_fund_overviewReport_bytType

import logging
logger = logging.getLogger('labsmanager')

class ExpensePOintViewSet(viewsets.ModelViewSet):
    queryset = Expense_point.objects.all()
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = serializers.ExpensePOintSerializer
    
    @action(methods=['get'], detail=False, url_path='current', url_name='current_expense')
    def lasts(self, request, pk=None):
      # queryset =  Expense_point.objects.filter(fund=18).annotate(ind=Concat(F('fund'), Value("-"), F('type'), output_field=CharField(),)) #.order_by('-value_date')
      # queryset=queryset.values('ind').annotate(max_date=Max('value_date'))
      
      # queryset =  Expense_point.objects.values('fund', 'type').annotate(max_date=Max('value_date'))
      queryset =  Expense_point.objects.values('fund', 'type').annotate(max_date=Max('value_date'))
      query=Q()
      for t in queryset:
        query |= (Q(fund=t["fund"]) & Q(type=t["type"]) & Q(value_date=t["max_date"]))
        
      
      queryset=Expense_point.objects.filter(query)
      return JsonResponse(self.serializer_class(queryset, many=True).data, safe=False)
 
from project.models import Participant 
from staff.models import Employee_Superior  
from settings.models import LabsManagerSetting
class ContractViewSet(viewsets.ModelViewSet):
    queryset = Contract.objects.select_related('employee', 'fund', 'contract_type').all()
    serializer_class = serializers.ContractSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = (filters.DjangoFilterBackend,)
    filterset_class = ContractFilter
    
    def get_queryset(self):
      # print("======================= [ContractViewSet] get_queryset ")
      if self.request is not None:
        ongoing = self.request.query_params.get('ongoing', None)
        if ongoing is not None:
          if ongoing == '1':
            qset = Contract.current.select_related('employee', 'fund', 'contract_type').all()
          else:
            qset = Contract.past.select_related('employee', 'fund', 'contract_type').all()
        else:
          qset = Contract.objects.select_related('employee', 'fund', 'contract_type').all() 
        # ====== Right Management
        qset = Contract.get_instances_for_user('view',self.request.user, qset )
        return qset
      return super().get_queryset()    
      
    
    def filter_queryset(self, queryset):
        params = self.request.query_params
          # print("[ContractViewSet.filter_queryset] start filtering")
        queryset = super().filter_queryset(queryset)
        
        is_active = params.get('active', None)
          # print("[ContractViewSet.filter_queryset] is_active:"+str(is_active))
        if is_active:
            queryset = queryset.filter(is_active=is_active)
            
        status = params.get('status', None) or params.get('cont_status', None)
        # print("[ContractViewSet.filter_queryset] status:"+str(status))
        if status:
            queryset = queryset.filter(status=status)
        
        name = params.get('name', None)
          # print("[ContractViewSet.filter_queryset] name:"+str(name))
        if name:
            queryset = queryset.filter( Q(employee__first_name__icontains=name) | Q(employee__last_name__icontains=name))
        
        typeC = params.get('type', None)
          # print("[ContractViewSet.filter_queryset] type:"+str(typeC))
        if typeC :
            queryset = queryset.filter(contract_type=typeC)
            
            
        pname = params.get('project_name', None)
          # print("[ContractViewSet.filter_queryset] name:"+str(pname))
        if pname:
            pjFund=Fund.objects.filter(project__name__icontains=pname).values('pk')
            queryset = queryset.filter(fund__in=pjFund)
            
        pid = params.get('project_id', None)
        if pid:
            pjFund=Fund.objects.filter(project__pk=pid).values('pk')
            queryset = queryset.filter(fund__in=pjFund)
            
            
        funder = params.get('funder', None)  
          # print("[ContractViewSet.filter_queryset] funder:"+str(funder))   
        if funder is not None :
            pjF=Fund.objects.filter(funder=funder).values('pk')
            queryset = queryset.filter(fund__in=pjF)
            
        institution_name= params.get('institution_name', None)  
          # print("[ContractViewSet.filter_queryset] institution_name:"+str(institution_name))   
        if institution_name is not None :
            pjI=Fund.objects.filter(institution=institution_name).values('pk')
            queryset = queryset.filter(fund__in=pjI)
            
        start_date= params.get('start', None) 
        if start_date is not None:
            if isinstance(start_date, list):
                start_date=start_date[0] 
            start_date=start_date.split("T")[0]
            query=Q(start_date__gte=start_date) | (Q(start_date__lt=start_date) & Q(end_date__gte=start_date))
            queryset= queryset.filter(query)
        
        end_date= params.get('end', None) 
        if end_date is not None:
            if isinstance(end_date, list):
                end_date=end_date[0]
            end_date=end_date.split("T")[0]
            query=Q(end_date__lte=end_date) | (Q(start_date__lt=end_date) & Q(end_date__gte=end_date))
            queryset= queryset.filter(query)
        
        isStale = params.get('stale', None)
          # print("[ContractViewSet.filter_queryset] isStale:"+str(isStale))
        
        if isStale is not None :
            if str2bool(isStale):
                queryset = queryset.filter(Contract.staleFilter())
            else:
                queryset = queryset.exclude(Contract.staleFilter())
        return queryset
    
    def list(self, request, *args, **kwargs):
        # print("======================= [ContractViewSet] list ")
        self.request = request
        export = request.GET.get('export', None)
        if export is not None:
            qs = self.filter_queryset(self.get_queryset())
            return self.download_queryset(qs, export)
        return super().list( request, *args, **kwargs)
      
    
    
    def download_queryset(self, queryset, export_format):
        """Download the filtered queryset as a data file"""
        dataset = ContractResource().export(queryset=queryset)
        filedata = dataset.export(export_format)
        dateSuffix=datetime.now().strftime("%Y%m%d-%H%M")
        filename = f"Contract_{dateSuffix}.{export_format}"
        return DownloadFile(filedata, filename)
        
    @action(methods=['get'], detail=True, url_path='contract_expense', url_name='contract_expense')
    def items(self, request, pk=None):
        cont = self.get_object()
        t1=Contract_expense.objects.filter(contract=cont.pk)
        return JsonResponse(serializers.ContractExpenseSerializer_min(t1, many=True).data, safe=False) 

    @action(methods=['get'], detail=False, url_path='stale', url_name='contract_stale')
    def get_stale(self, request):
        slots=getDashboardContractTimeSlot(request)
        cont=Contract.current.timeframe(slots).select_related('employee', 'fund', 'contract_type').filter( Q(fund__project__status=True) & Q(is_active=True)).order_by('-end_date')
        return JsonResponse(serializers.ContractSerializer(cont, many=True).data, safe=False) 
      
    @action(methods=['get'], detail=False, url_path='contract_calendar', url_name='contract_calendar')
    def get_contract_cal(self, request):
        qset=self.filter_queryset(self.queryset)
        return JsonResponse(serializers.ContractSerializer1DCal(qset, many=True).data, safe=False) 
    
    @action(methods=['get'], detail=False, url_path='contract_fund_modal/(?P<fund_id>[0-9]+)', url_name='contract_fund_modal')
    def get_contract_fund_modal(self, request, fund_id):
        qset = Contract.objects.futur().select_related('employee', 'fund', 'contract_type').all()
        qset=self.filter_queryset(qset)
        qset=qset.filter(fund=fund_id)
        data = {'contracts': qset}
        fu = Fund.objects.get(pk=fund_id)
        data["fund"]= fu
        
        fuT = Fund_Item.objects.filter(fund=fu) # get_fund_overviewReport_bytType(fund_id)
        data["fund_overview"]=fuT
        
        
        
        effe = qset.filter(status='effe')
        effe_am = 0
        effe_am_left = 0
        for c in effe :
            effe_am += c.total_amount
            effe_am_left += c.remain_amount
            
        data["effective_amount"]=effe_am
        data["effective_amount_left"]=effe_am_left
        
        prov = qset.filter(status='prov')
        prov_am = 0
        prov_am_left = 0
        for c in prov :
            prov_am += c.total_amount
            prov_am_left += c.remain_amount
            
        data["prov_amount"]=prov_am
        data["prov_amount_left"]=prov_am_left
        
        data["total_amount_left"]=fu.available_f-effe_am_left-prov_am_left
        return render(request, 'expense/contract_fund_modal.html', data)
        
      
    # methods to manage calendar API call
    
    @action(methods=['post'], detail=False, url_path='contract_add', url_name='contract_add')
    def add_contract(self, request):
        emp = Employee.objects.get(pk=request.data['employee'])
        if(not emp):
          raise ObjectDoesNotExist(f" Employee '{request.data['employee']}' not found in database")
        # emp = emp.first()
        fu = Fund.objects.get(pk=request.data['fund'])
        if(not emp):
          raise ObjectDoesNotExist(f" Fund '{request.data['employee']}' not found in database")
        cont=Contract(
          employee = emp,
          fund = fu,
          start_date = request.data['start_date'],
          end_date = request.data['end_date'],
          is_active =False,
          status = "prov",          
        )
        cont.save()
        return HttpResponse("Ok")
      
    @action(methods=['post'], detail=False, url_path='contract_update', url_name='contract_update')
    def update_contract(self, request):
        cont = Contract.objects.get(pk=request.data['pk'])
        if(not cont):
          raise ObjectDoesNotExist(f" Contract '{request.data['pk']}' not found in database")
        
        if("employee" in request.data):
          emp = Employee.objects.get(pk=request.data['employee'])
          if(not emp):
            raise ObjectDoesNotExist(f" Employee '{request.data['employee']}' not found in database")
          cont.employee = emp
          
        if("start_date" in request.data):
          cont.start_date = request.data['start_date']
          
        if("end_date" in request.data):
          cont.end_date = request.data['end_date']  
        result = cont.save()
        return HttpResponse(f"Ok :{result}")