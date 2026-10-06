
from rest_framework import serializers
from .models import Expense_point


class absoluteField(serializers.Field):
    def to_representation(self, value):
        return abs(value)
    

class ProjectExpensePointGraphSerializer(serializers.ModelSerializer):
    funder = serializers.CharField(source='fund.funder.short_name')
    institution = serializers.CharField(source='fund.institution.short_name')
    type = serializers.CharField(source='type.short_name')
    ref = serializers.CharField(source='fund.ref')
    date =serializers.DateField(source='value_date') 
    amount= absoluteField()
    class Meta:
        model = Expense_point
        fields = ['date', 'funder', 'ref', 'institution', 'type', 'amount']   