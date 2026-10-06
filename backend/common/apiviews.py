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
from .preferences import visible_user_relations


class favoriteViewSet(viewsets.ModelViewSet):
    queryset = favorite.objects.select_related('user').all()
    serializer_class = serializers.FavoriteSerialize
    permission_classes = [permissions.IsAuthenticated]
    http_method_names = ["get", "delete", "head", "options"]

    def get_queryset(self):
        ids = [relation.pk for _, relation, _ in visible_user_relations(self.request.user, favorite)]
        return favorite.objects.filter(user=self.request.user, pk__in=ids).select_related("user", "content_type")
    
    @action(methods=['get'], detail=False, url_path='current_user', url_name='current_user')
    def genericinfotype(self, request):
        
        sub=self.get_queryset()
        sub = sorted(sub, key=lambda x: (x.content_type.name, x.content_object.__str__()))
        return JsonResponse(serializers.FavoriteSerialize(sub, many=True).data, safe=False)
    
    
class subscriptionViewSet(viewsets.ModelViewSet):
    queryset = subscription.objects.select_related('user').all()
    serializer_class = serializers.FavoriteSerialize
    permission_classes = [permissions.IsAuthenticated]
    http_method_names = ["get", "delete", "head", "options"]

    def get_queryset(self):
        ids = [relation.pk for _, relation, _ in visible_user_relations(self.request.user, subscription)]
        return subscription.objects.filter(user=self.request.user, pk__in=ids).select_related("user", "content_type")
    
    
    @action(methods=['get'], detail=False, url_path='current_user', url_name='current_user')
    def genericinfotype(self, request):
        
        sub=self.get_queryset().order_by("content_type")
        sub = sorted(sub, key=lambda x: (x.content_type.name, x.content_object.__str__()))
        return JsonResponse(serializers.FavoriteSerialize(sub, many=True).data, safe=False)
