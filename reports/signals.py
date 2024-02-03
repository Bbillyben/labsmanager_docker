
import os

from django.utils.translation import gettext_lazy as _
from django.core.cache import cache

import logging
logger = logging.getLogger('labsmanager')

# @receiver(post_delete, sender=EmployeePDFReport)
def auto_delete_templatefile_on_delete(sender, instance, **kwargs):
    """
    Deletes file from filesystem
    when corresponding `TemplateReport` object is deleted.
    Connection with signal is done in 'def __init_subclass__(cls, **kwargs):' from TemplateReport class
    """
    if instance.template:
        if os.path.isfile(instance.template.path):
            logger.debug(" > TemplateReport post delete ----------")
            logger.debug(f'  - deleting file : {instance.template.path}')
            cache.delete(instance.template.path)
            os.remove(instance.template.path)