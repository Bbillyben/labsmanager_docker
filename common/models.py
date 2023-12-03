from django.db import models
from django.utils.translation import gettext_lazy as _
from django.contrib.auth.models import User

from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType


class favorite(models.Model):
    user = models.ForeignKey(User, null=False, blank=False, on_delete=models.CASCADE, verbose_name=_('User'))
    content_type = models.ForeignKey(ContentType, related_name="content_type_favorite", on_delete=models.CASCADE, )
    object_id = models.PositiveIntegerField()
    content_object = GenericForeignKey('content_type', 'object_id')
    
    
    def __str__(self):
        return f"{self.user.username} : {self.content_object.__str__()}"

class subscription(models.Model):
    user = models.ForeignKey(User, null=False, blank=False, on_delete=models.CASCADE, verbose_name=_('User'))
    content_type = models.ForeignKey(ContentType, related_name="content_type_subscription", on_delete=models.CASCADE, )
    object_id = models.PositiveIntegerField()
    content_object = GenericForeignKey('content_type', 'object_id')
    
    def __str__(self):
        return f"{self.user.username} : {self.content_object.__str__()}"
    
    
    
################## For User customs permissions #######################################################
#######################################################################################################
        
class RightsSupport(models.Model):
            
    class Meta:
        
        managed = False  # No database table creation or deletion  \
                         # operations will be performed for this model. 
                
        default_permissions = ("view") # disable "add", "change", "delete"
                                 # and "view" default permissions

        permissions = ( 
            ('employee_list', 'Permission to see employee list'),  
            ('team_list', 'Permission to see team list'), 
            ('project_list', 'Permission to see project list'),
            ('display_calendar', 'Permission to see main calendar'),
            ('display_dashboard', 'Permission to see dasgboard'), 
        )

# from django.contrib.auth.models import Permission, Group
# from django.db import models

# class PermEmployeeList(Permission):
#     class Meta:
#         verbose_name = 'permission Employee list'
        
# class PermProjectList(Permission):
#     class Meta:
#         verbose_name = 'permission Project list'

# class PermBrowseFundList(Permission):
#     class Meta:
#         verbose_name = 'permission Project list'

# class PermCalendar(Permission):
#     class Meta:
#         verbose_name = 'permission Full Calendar'
        
# class PermDashboard(Permission):
#     class Meta:
#         verbose_name = 'permission Dashboard'
        
# class CustomPermissionSet(models.Model):
#     name = models.CharField(max_length=255)
#     permissions = models.ManyToManyField(
#         'common.PermEmployeeList', 
#         'common.PermProjectList', 
#         'common.PermBrowseFundList', 
#         'common.PermCalendar', 
#         'common.PermDashboard')

#     def __str__(self):
#         return self.name