from django.db import models
from django.utils.translation import gettext_lazy as _
from django.core.validators import MaxLengthValidator

from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType


from faicon.fields import FAIconField
from auditlog.models import AuditlogHistoryField
from auditlog.registry import auditlog

####################### GENERAL Informations #################
######  informations about institution or funder
## 1 type / icon + name
## 2 info with generic foreign key

class OrganizationInfosType(models.Model):
    class Meta:
        """Metaclass defines extra model properties"""
        verbose_name = _("Type of Organization Info")
    
    name = models.CharField(max_length=50, unique=True, verbose_name=_('Name'))
    icon = FAIconField(null=True,)
    
    def __str__(self):
       return self.name

class OrganizationInfos(models.Model):
    class Meta:
        """Metaclass defines extra model properties"""
        verbose_name = _("Organization Info")
    
    #orga = models.ForeignKey(Project, on_delete=models.CASCADE, verbose_name=_('Project'))
    content_type = models.ForeignKey(ContentType, related_name="content_type_oragnization", on_delete=models.CASCADE, )
    object_id = models.PositiveIntegerField()
    content_object = GenericForeignKey('content_type', 'object_id')
    
    info =  models.ForeignKey(OrganizationInfosType, on_delete=models.CASCADE, verbose_name=_('Info Type'))
    value = models.CharField(max_length=150, blank=True, null=True, verbose_name=_('Info Value'))
    comment = models.TextField(max_length=350, blank=True, null=True, verbose_name=_('comment'))
    history = AuditlogHistoryField()

    def __str__(self):
       return f'{self.info.name} - {self.value}'
    
    
########################## CONTACT ##########################
##### Contact for insitution or funder
## 1 type of contact
## 2 contact with foregin key + free comment

##### Contact information 
## 1 type of information (eg tel, mail, ) / icon + name
## 2 infos / contact + type + value


class ContactType(models.Model):
    class Meta:
        """Metaclass defines extra model properties"""
        verbose_name = _("Type of Contact")
    
    name = models.CharField(max_length=50, unique=True, verbose_name=_('Name'))
    
    def __str__(self):
       return self.name

class ContactInfoType(models.Model):
    class Meta:
        """Metaclass defines extra model properties"""
        verbose_name = _("Type of Contact Info")
    
    name = models.CharField(max_length=50, unique=True, verbose_name=_('Name'))
    icon = FAIconField(null=True,)
    
    def __str__(self):
       return self.name



class Contact(models.Model):
    class Meta:
        """Metaclass defines extra model properties"""
        verbose_name = _("Organization's Contact")
        
        
    content_type = models.ForeignKey(ContentType, related_name="content_type_contact", on_delete=models.CASCADE, )
    object_id = models.PositiveIntegerField()
    content_object = GenericForeignKey('content_type', 'object_id')
    
    first_name = models.CharField(max_length=50, unique=True, verbose_name=_('First Name'))
    last_name = models.CharField(max_length=50, unique=True, verbose_name=_('Last Name'))  
    type =  models.ForeignKey(ContactType, on_delete=models.CASCADE, verbose_name=_('Contact Type'))
    comment = models.TextField(max_length=350, blank=True, null=True, verbose_name=_('comment'))
    history = AuditlogHistoryField()

    def __str__(self):
       return f'{self.first_name} {self.last_name} - {self.content_object}'

class ContactInfo(models.Model):
    class Meta:
        """Metaclass defines extra model properties"""
        verbose_name = _("Contact Info")

    contact =  models.ForeignKey(Contact, on_delete=models.CASCADE, verbose_name=_('Contact'))
    info =  models.ForeignKey(ContactInfoType, on_delete=models.CASCADE, verbose_name=_('Contact Info Type'))
    value = models.CharField(max_length=150, blank=True, null=True, verbose_name=_('Info Value'))
    comment = models.CharField(max_length=150, blank=True, null=True, verbose_name=_('comment'))
    
    def __str__(self):
       return f'{self.contact.first_name} {self.contact.last_name} - {self.info.name}'
    
auditlog.register(OrganizationInfos)
auditlog.register(Contact)