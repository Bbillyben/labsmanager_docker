from django.db import models
from django.db.models import Q
from datetime import date


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