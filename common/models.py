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

class subscription(models.Model):
    user = models.ForeignKey(User, null=False, blank=False, on_delete=models.CASCADE, verbose_name=_('User'))
    content_type = models.ForeignKey(ContentType, related_name="content_type_subscription", on_delete=models.CASCADE, )
    object_id = models.PositiveIntegerField()
    content_object = GenericForeignKey('content_type', 'object_id')
    
    class Meta:
        ordering = ['content_type']
    
    def __str__(self):
        return f"{self.user.username} : {self.content_object.__str__()}"