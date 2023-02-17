from django.http import JsonResponse
from django.db.models import Q, F, ExpressionWrapper, fields
from django.db.models.functions import Cast, Coalesce, Now, Extract, Abs
from datetime import datetime

from rest_framework import viewsets, permissions
from rest_framework.response import Response
from rest_framework.decorators import action
from django_filters import rest_framework as filters
from labsmanager import serializers 

from .models import favorite

class favoriteViewSet(viewsets.ModelViewSet):
    queryset = favorite.objects.select_related('user').all()
    serializer_class = serializers.FavoriteSerialize
    permission_classes = [permissions.IsAuthenticated]