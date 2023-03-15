from rest_framework import serializers
from fund.models import Fund, Fund_Item
from labsmanager import serializers as lserial

class FundItemReportSerialize_min(serializers.ModelSerializer):
    type=lserial.CostTypeSerialize(many=False, read_only=True)
    class Meta:
        model = Fund_Item
        fields = ['pk', 'type', 'amount','expense','value_date', 'available', 'entry_date',]  
        
class FundProjectReportSerializer(serializers.ModelSerializer):
    funder=lserial.Fund_InstitutionSerializer(many=False, read_only=True)
    institution=lserial.InstitutionSerializer(many=False, read_only=True)
    fund_item=FundItemReportSerialize_min(many=True, read_only=True)
    class Meta:
        model = Fund
        fields = ['pk', 'funder', 'institution', 'ref','start_date', 'end_date', 
                  'amount', 'expense','available',
                  'fund_item',
                ] 
        
