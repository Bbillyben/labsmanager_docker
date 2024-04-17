from django.db import models
from django.db.models import Q, Max
from datetime import date
from collections.abc import Iterable
from labsmanager.manager import date_manager

class effective_Manager(date_manager):
        
    def get_queryset(self):
        query = Q(status="effe")
        return super().get_queryset().filter(query)
    
class provisionnal_Manager(date_manager):
    
    def get_queryset(self):
        query = Q(status="prov")
        return super().get_queryset().filter(query)