from django.db.models import Q
from .models import Employee
from django_filters import rest_framework as filters
import django_filters

class EmployeeFilter(filters.FilterSet):
    """ set filter for django.filters"""
    
    entry_date = filters.NumberFilter(field_name='entry_date', lookup_expr='year')
    entry_date__gt = filters.NumberFilter(field_name='entry_date', lookup_expr='year__gt')
    entry_date__lt = filters.NumberFilter(field_name='entry_date', lookup_expr='year__lt')
    
    exit_date = filters.NumberFilter(field_name='exit_date', lookup_expr='year')
    exit_date__gt = filters.NumberFilter(field_name='exit_date', lookup_expr='year__gt')
    exit_date__lt = filters.NumberFilter(field_name='exit_date', lookup_expr='year__lt')
    
    user__name =  filters.CharFilter(field_name='first_name', lookup_expr='icontains')
    is_active = filters.BooleanFilter(field_name='is_active', lookup_expr='isnull')
    name=filters.CharFilter(method='name_search')
    class Meta:
        model = Employee
        fields = ['first_name','last_name', 'name', 'entry_date', 'exit_date', 'is_active',]
    
    def name_search(self, queryset, name, value):
        return queryset.filter(
            Q(first_name__icontains=value) | Q(last_name__icontains=value)
        )