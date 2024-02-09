from django.http import HttpResponse
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _

from .views import FundItemImportView
from labsmanager.helpers import DownloadFile

def get_import_template(request):
    '''Create an empty export file to provide a template for importing data
    '''
    res_id=request.GET.get('resource', None)
    export = request.GET.get('export', None)
    
    if not res_id or not export:
        raise ValidationError(_('Resource Id (%s) and export format (%s) should be set') % (res_id, export))
    
    # get resource from importView
    try:
        res_class = FundItemImportView.resource_classes[int(res_id)]
    except:
        raise ValidationError(_('ResourceNot Found'))
    
    model = res_class._meta.model

    qs = model.objects.none()

    dataset = res_class().export(queryset=qs)
    filedata = dataset.export(export)
    filename = f"{res_class._meta.name}_template.{export}"
    return DownloadFile(filedata, filename)

    
    