from django.db.models import Q
from .models import Contract
from django_filters import rest_framework as filters
import django_filters



class ContractFilter(filters.FilterSet):
    class Meta:
        mode:Contract
        fields=['employee', 'start_date', 'end_date', 'name']
