from django.http import JsonResponse
from django.db.models import Q, Value, Count, F, CharField, Max
from django.db.models.functions import Concat


from rest_framework import viewsets, permissions
from rest_framework.decorators import action
from django_filters import rest_framework as filters
from labsmanager import serializers  # UserSerializer, GroupSerializer, EmployeeSerialize, EmployeeStatusSerialize, ContractEmployeeSerializer, TeamSerializer, ParticipantSerializer, ProjectSerializer
from expense.models import Expense_point, Contract, Contract_expense
from .resources import ContractResource
from labsmanager.helpers import DownloadFile

from labsmanager.utils import str2bool
from staff.filters import EmployeeFilter
from expense.filters import ContractFilter
from project.models import Project
from fund.models import Fund
from dashboard.utils import getDashboardContractTimeSlot

from datetime import datetime

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
      
class ContractViewSet(viewsets.ModelViewSet):
    queryset = Contract.objects.select_related('employee', 'fund', 'contract_type').all()
    serializer_class = serializers.ContractSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = (filters.DjangoFilterBackend,)
    filterset_class = ContractFilter
    
    def get_queryset(self):
      
      if self.request is not None:
        ongoing = self.request.query_params.get('ongoing', None)
        if ongoing is not None:
          if ongoing == '1':
            return Contract.current.select_related('employee', 'fund', 'contract_type').all()
          else:
            return Contract.past.select_related('employee', 'fund', 'contract_type').all()
      return super().get_queryset()    
      
    
    def filter_queryset(self, queryset):
        params = self.request.query_params
          # print("[ContractViewSet.filter_queryset] start filtering")
        queryset = super().filter_queryset(queryset)
        
        is_active = params.get('active', None)
          # print("[ContractViewSet.filter_queryset] is_active:"+str(is_active))
        if is_active:
            queryset = queryset.filter(is_active=is_active)
        
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
        print("[ContractViewSet.filter_queryset] pid:"+str(pid))
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
        
        isStale = params.get('stale', None)
          # print("[ContractViewSet.filter_queryset] isStale:"+str(isStale))
        
        if isStale is not None :
            if str2bool(isStale):
                queryset = queryset.filter(Contract.staleFilter())
            else:
                queryset = queryset.exclude(Contract.staleFilter())
        return queryset
    
    def list(self, request, *args, **kwargs):
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
        