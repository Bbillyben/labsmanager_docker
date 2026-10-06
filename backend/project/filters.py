from django.db.models import Q
from .models import Project
from django_filters import rest_framework as filters

class ProjectFilter(filters.FilterSet):
    
    class Meta:
        model = Project
        fields = ['name','start_date', 'end_date', 'status',]
    