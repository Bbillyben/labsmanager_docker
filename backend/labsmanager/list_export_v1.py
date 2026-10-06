"""File response for the existing Employee and Project list Resources."""

from django.http import HttpResponse
from django.utils import timezone
from import_export.formats.base_formats import CSV, TSV, XLS, XLSX
from rest_framework.negotiation import DefaultContentNegotiation
from rest_framework.exceptions import ValidationError


EXPORT_FORMATS = {"csv": CSV, "tsv": TSV, "xls": XLS, "xlsx": XLSX}


class ListExportContentNegotiation(DefaultContentNegotiation):
    """Reserve ?format= for the file type instead of DRF's JSON renderer override."""

    def select_renderer(self, request, renderers, format_suffix=None):
        return renderers[0], renderers[0].media_type


def export_list_queryset(request, queryset, resource_class, filename_prefix, *, resource_kwargs=None):
    format_name = request.query_params.get("format", "xlsx")
    if format_name not in EXPORT_FORMATS:
        raise ValidationError({"format": "Choose csv, tsv, xls, or xlsx."})

    file_format = EXPORT_FORMATS[format_name]()
    dataset = resource_class(**(resource_kwargs or {})).export(queryset=queryset)
    response = HttpResponse(file_format.export_data(dataset), content_type=file_format.CONTENT_TYPE)
    filename = f"{filename_prefix}_{timezone.localtime():%Y%m%d-%H%M}.{file_format.get_extension()}"
    response["Content-Disposition"] = f'attachment; filename="{filename}"'
    return response
