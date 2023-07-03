from django.http import JsonResponse
from django.db.models import Q, F, ExpressionWrapper, fields
from django.db.models.functions import Cast, Coalesce, Now, Extract, Abs
from datetime import datetime

from rest_framework import viewsets, permissions
from rest_framework.response import Response
from rest_framework.decorators import action
from django_filters import rest_framework as filters
from labsmanager import serializers 

from .models import favorite, subscription


class favoriteViewSet(viewsets.ModelViewSet):
    queryset = favorite.objects.select_related('user').all()
    serializer_class = serializers.FavoriteSerialize
    permission_classes = [permissions.IsAuthenticated]
    
    
class subscriptionViewSet(viewsets.ModelViewSet):
    queryset = subscription.objects.select_related('user').all()
    serializer_class = serializers.FavoriteSerialize
    permission_classes = [permissions.IsAuthenticated]
    
    
    @action(methods=['get'], detail=False, url_path='current_user', url_name='current_user')
    def genericinfotype(self, request):
        
        sub=subscription.objects.filter(user=request.user)
        
        return JsonResponse(serializers.FavoriteSerialize(sub, many=True).data, safe=False)