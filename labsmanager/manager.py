from django.db import models
from django.db.models import Q
from datetime import date

class Current_date_Manager(models.Manager):
    def get_queryset(self):
        cdate = date.today()
        query = (Q(start_date__lte=cdate) | Q(start_date=None)) & (Q(end_date__gte=cdate) | Q(end_date=None))
        
        return super().get_queryset().filter(query)