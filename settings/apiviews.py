
from rest_framework import generics, status, viewsets, permissions
from rest_framework.permissions import IsAuthenticated
from . import models, serializers


class UserSettingsDetail(generics.RetrieveUpdateAPIView):
    """Detail view for an individual "user setting" object.
    - User can only view / edit settings their own settings objects
    """

    lookup_field = 'key'
    queryset = models.LMUserSetting.objects.all()
    serializer_class = serializers.UserSettingsSerializer

    def get_object(self):
        """Attempt to find a user setting object with the provided key."""
        key = self.kwargs['key']

        if key not in models.LMUserSetting.SETTINGS.keys():
            raise NotFound()

        return models.LMUserSetting.get_setting_object(key, user=self.request.user)
    
    permission_classes = (IsAuthenticated,)
    
    
class UserSettingsList(generics.ListAPIView):
    """API endpoint for accessing a list of user settings objects."""

    queryset = models.LMUserSetting.objects.all()
    serializer_class = serializers.UserSettingsSerializer

    def filter_queryset(self, queryset):
        """Only list settings which apply to the current user."""
        try:
            user = self.request.user
        except AttributeError:  # pragma: no cover
            return models.LMUserSetting.objects.none()

        queryset = super().filter_queryset(queryset)

        queryset = queryset.filter(user=user)

        return queryset
    
    permission_classes = (IsAuthenticated,)
    
    


class GlobalSettingsList(generics.ListAPIView):
    """API endpoint for accessing a list of global settings objects."""

    queryset = models.LabsManagerSetting.objects.all()
    serializer_class = serializers.GlobalSettingsSerializer
    

class GlobalSettingsDetail(generics.RetrieveUpdateAPIView):
    """Detail view for an individual "global setting" object.
    - User must have 'staff' status to view / edit
    """

    lookup_field = 'key'
    queryset = models.LabsManagerSetting.objects.all()
    serializer_class = serializers.GlobalSettingsSerializer

    def get_object(self):
        """Attempt to find a global setting object with the provided key."""
        key = self.kwargs['key']

        if key not in models.LabsManagerSetting.SETTINGS.keys():
            raise NotFound()

        return models.LabsManagerSetting.get_setting_object(key)

    permission_classes = [
        permissions.IsAuthenticated,
    ]