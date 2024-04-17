from django.db import models
from django.db.models import Q, Max
from datetime import date
from collections.abc import Iterable

class date_manager(models.Manager):
    def timeframe(self, slots):
        query=Q()
        if 'from' in slots:
            query= query & Q(end_date__gte=slots["from"])
        if 'to' in slots:
            query= query & Q(start_date__lte=slots["to"])
        return self.get_queryset().filter(query)
    
    def current(self):
        cdate = date.today()
        query = (Q(start_date__lte=cdate) | Q(start_date=None)) & (Q(end_date__gte=cdate) | Q(end_date=None))
        return self.get_queryset().filter(query)
    
    def futur(self):
        cdate = date.today()
        query = Q(start_date__gte=cdate) | Q(end_date__gte=cdate)
        return self.get_queryset().filter(query)

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
    
class futur_date_Manager(date_manager):
    def get_queryset(self):
        cdate = date.today()
        query = Q(start_date__gte=cdate) | Q(end_date__gte=cdate)
        
        return super().get_queryset().filter(query)

  
    
class LastInManager(models.Manager):
    
    def get_queryset(self, sel_fund=None):
        # print("---------> LastInManager - get_queryset :"+str(self.model))
        # print("  - sel_fund : "+str(sel_fund))
        queryset = super().get_queryset()
        if sel_fund is not None:
            # print(" type : "+str(type(sel_fund)))
            if isinstance(sel_fund, str):
                sel_fund=sel_fund.split(",")
                # print("  - trsf sel fund : "+str(sel_fund))
            elif isinstance(sel_fund, int):
                sel_fund=[sel_fund]
                
            try:
                queryset=queryset.filter(fund__in=sel_fund)
                # print("  - fund found : "+str(queryset.count()))
            except:
                queryset = None
                # print("  IN ERROR")
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
    
    
class focus_manager(models.Manager):
    def get_queryset(self):
        return super().get_queryset().filter(type__in_focus=True)
    
    
class FileModelManager(models.Manager):
    def contribute_to_class(self, model, name):
        super(FileModelManager, self).contribute_to_class(model, name)
        self._bind_flush_signal(model)
        
    def _bind_flush_signal(self, model):
        models.signals.post_delete.connect(flush_file, model)

import os   
def flush_file(sender, **kwargs):
    print(" -- flush_file called --")
    print("  - sender:"+str(sender))
    print("  - kwargs:"+str(kwargs))
    
    instance = kwargs.pop('instance', False)

    if instance.template:
        if os.path.isfile(instance.template.path):
            os.remove(instance.template.path)