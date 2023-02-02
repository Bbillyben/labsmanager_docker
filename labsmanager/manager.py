from django.db import models
from django.db.models import Q, Max
from datetime import date
from collections.abc import Iterable

class date_manager(models.Manager):
    def timeframe(self, slots):
        queryset=super().get_queryset()
        if 'from' in slots:
            queryset = queryset.filter(Q(end_date__gte=slots["from"]))
        if 'to' in slots:
            queryset = queryset.filter(Q(end_date__lte=slots["to"]))
        return queryset

class Current_date_Manager(date_manager):
    def get_queryset(self):
        cdate = date.today()
        query = (Q(start_date__lte=cdate) | Q(start_date=None)) & (Q(end_date__gte=cdate) | Q(end_date=None))
        
        return super().get_queryset().filter(query)
    
class outof_date_Manager(date_manager):
    def get_queryset(self):
        cdate = date.today()
        query = Q(start_date__gte=cdate) | Q(end_date__lte=cdate)
        
        return super().get_queryset().filter(query)
    
    
class LastInManager(models.Manager):
    
    def get_queryset(self, sel_fund=None):
        print("---------> LastInManager - get_queryset")
        print("  - sel_fund : "+str(sel_fund))
        queryset = super().get_queryset()
        if sel_fund is not None:
            if not isinstance(sel_fund, Iterable):
                sel_fund=[sel_fund]
            try:
                queryset=queryset.filter(fund__in=sel_fund)
            except:
                pass
        if not queryset:
            return super().get_queryset().none()
        
        queryset =  queryset.values('fund', 'type').annotate(max_date=Max('value_date'))
        query=Q()
        for t in queryset:
            query |= (Q(fund=t["fund"]) & Q(type=t["type"]) & Q(value_date=t["max_date"]))
        
        return super().get_queryset().filter(query)
    
    def fund(self, sel_fund):
        return self.get_queryset(sel_fund)