"""Session-based import workflow backed exclusively by django-import-export."""

import csv
import io
import json
import tempfile
import time
import uuid
from html.parser import HTMLParser
from pathlib import Path

import tablib
from django.core import signing
from django.conf import settings
from django.contrib.admin.models import ADDITION, CHANGE, LogEntry
from django.contrib.contenttypes.models import ContentType
from django.http import HttpResponse
from django.utils.translation import gettext as _
from import_export.formats import base_formats
from import_export.signals import post_import
from rest_framework.authentication import SessionAuthentication
from rest_framework.exceptions import NotFound, PermissionDenied, ValidationError
from rest_framework.permissions import IsAuthenticated
from labsmanager.list_export_v1 import ListExportContentNegotiation
from rest_framework.response import Response
from rest_framework.views import APIView

from .profiles import PROFILES


FORMAT_CLASSES = {name: cls for name, cls in (
    ("csv", base_formats.CSV), ("tsv", base_formats.TSV),
    ("xls", base_formats.XLS), ("xlsx", base_formats.XLSX),
)}
TOKEN_AGE = 3600
MAX_FILE_SIZE = 10 * 1024 * 1024
TOKEN_SALT = "labsmanager-import-v1"
TEMP_DIR = Path(tempfile.gettempdir()) / "labsmanager-import-v1"


class ChangeText(HTMLParser):
    """Read the old/new values from the Resource's HTML diff without serving HTML."""

    def __init__(self):
        super().__init__()
        self.mode = None
        self.old = []
        self.new = []

    def handle_starttag(self, tag, attrs):
        if tag in ("del", "ins"):
            self.mode = tag

    def handle_endtag(self, tag):
        if tag == self.mode:
            self.mode = None

    def handle_data(self, data):
        if self.mode == "del":
            self.old.append(data)
        elif self.mode == "ins":
            self.new.append(data)
        else:
            self.old.append(data)
            self.new.append(data)

    def values(self, html):
        self.mode, self.old, self.new = None, [], []
        self.feed(str(html or ""))
        return "".join(self.old).strip(), "".join(self.new).strip()


def _temp_path(identifier):
    try:
        uuid.UUID(identifier)
    except (TypeError, ValueError):
        raise ValidationError({"import_token": _("Invalid import token")})
    return TEMP_DIR / identifier


def _clean_expired():
    TEMP_DIR.mkdir(mode=0o700, parents=True, exist_ok=True)
    cutoff = time.time() - TOKEN_AGE
    for path in TEMP_DIR.iterdir():
        if path.is_file() and path.stat().st_mtime < cutoff:
            path.unlink(missing_ok=True)


def _sign(user, profile, identifier, file_format, sheet=None, previewed=False, preview_id=None):
    return signing.dumps({"user": user.pk, "profile": profile.key, "file": identifier,
                          "format": file_format, "sheet": sheet, "previewed": previewed,
                          "preview_id": preview_id}, salt=TOKEN_SALT)


def _read_token(token, user, profile, *, previewed=None):
    try:
        value = signing.loads(token, salt=TOKEN_SALT, max_age=TOKEN_AGE)
    except (signing.BadSignature, signing.SignatureExpired, TypeError):
        raise ValidationError({"import_token": _("Invalid or expired import token")})
    if value.get("user") != user.pk or value.get("profile") != profile.key:
        raise PermissionDenied(_("This import does not belong to you"))
    if previewed is not None and value.get("previewed") != previewed:
        raise ValidationError({"import_token": _("Preview the import before confirming")})
    path = _temp_path(value.get("file"))
    if not path.is_file():
        raise ValidationError({"import_token": _("Import file has expired")})
    return value, path


def _datasets(data, file_format):
    try:
        if file_format in ("xls", "xlsx"):
            return {sheet.title: sheet for sheet in tablib.import_book(data, format=file_format).sheets()}
        dataset = FORMAT_CLASSES[file_format](encoding="utf-8-sig").create_dataset(data)
        return {"": dataset}
    except Exception:
        raise ValidationError({"file": _("File cannot be read in the selected format")})


def _dataset(value, path, *, sheet=None):
    datasets = _datasets(path.read_bytes(), value["format"])
    name = value.get("sheet") if sheet is None else sheet
    if name is None and len(datasets) == 1:
        name = next(iter(datasets))
    if name not in datasets:
        raise ValidationError({"sheet": _("Sheet not found")})
    if not datasets[name].headers:
        raise ValidationError({"sheet": _("Selected sheet has no header row")})
    return datasets[name], name


def _structure(resource, dataset):
    expected = [field.column_name for field in resource.get_import_fields()]
    actual = list(dataset.headers or [])
    return {"expected": expected, "recognized": [h for h in actual if h in expected],
            "missing": [h for h in expected if h not in actual],
            "extra": [h for h in actual if h not in expected],
            "columns": len(actual), "rows": len(dataset)}


def _import_dataset(resource, dataset):
    """Treat a blank CSV identifier like an empty Excel identifier cell."""
    headers = list(dataset.headers or [])
    identifiers = {field.column_name for field in resource.get_fields()
                   if field.attribute in (resource._meta.import_id_fields or ("id",))}
    if not identifiers.intersection(headers):
        return dataset
    return tablib.Dataset(*[
        [None if header in identifiers and value == "" else value
         for header, value in zip(headers, values)] for values in dataset
    ], headers=headers)


def _preview_path(file_id, preview_id):
    _temp_path(file_id)
    try:
        uuid.UUID(preview_id)
    except (TypeError, ValueError):
        raise ValidationError({"import_token": _("Invalid import token")})
    return TEMP_DIR / f"{file_id}.{preview_id}.errors"


def _error_message(row):
    messages = [str(error.error) for error in row.errors]
    if row.validation_error:
        messages.extend(str(item) for item in row.validation_error.messages)
    # SkipErrorRessource converts errors into skipped rows and puts the message
    # in the last diff cell. The legacy import can still commit other rows.
    if row.import_type == "skip" and row.diff and str(row.diff[-1]).startswith("Errors: "):
        messages.append(str(row.diff[-1])[8:])
    return "\n".join(messages)


def _normalize(result, dataset, resource, profile):
    headers = list(dataset.headers or [])
    key_fields = list(resource._meta.import_id_fields or ("id",))
    fields = {field.attribute: field.column_name for field in resource.get_fields()}
    key_headers = [fields.get(key, key) for key in key_fields]
    if profile.identity_columns:
        key_headers = profile.identity_columns
    clean = ChangeText()
    preview_fields = profile.preview_fields(resource)
    # The Resource has already exported the resolved instance for its diff. Reuse
    # those values rather than resolving each relation again for the table.
    visible_fields = resource.get_user_visible_fields()
    diff_positions = {id(field): index for index, field in enumerate(visible_fields)}

    def preview_values(source, row, state):
        values = {}
        for name, field in preview_fields:
            raw = source.get(field.column_name)
            value = raw
            position = diff_positions.get(id(field))
            if state != "error" and row is not None and row.diff and position is not None and position < len(row.diff):
                _, resolved = clean.values(row.diff[position])
                if resolved or raw in (None, ""):
                    value = resolved
            values[name] = str(value) if value is not None else ""
        return values

    rows = []
    counts = {"new": 0, "update": 0, "unchanged": 0, "error": 0}
    for index, row in enumerate(result.rows):
        source = dict(zip(headers, dataset[index])) if index < len(dataset) else {}
        message = _error_message(row)
        state = "error" if message else {"new": "new", "update": "update", "skip": "unchanged",
                                           "error": "error", "invalid": "error"}.get(row.import_type, "error")
        counts[state] += 1
        diff = []
        if state == "update":
            for header, item in zip(result.diff_headers, row.diff or []):
                old, new = clean.values(item)
                if old != new:
                    diff.append({"field": str(header), "old": old, "new": new})
        values = [str(source.get(key)) for key in key_headers if source.get(key) not in (None, "")]
        identity = " ".join(values) if profile.join_identity else (values[0] if values else "")
        rows.append({"row_number": index + 2, "state": state, "identity": identity,
                     "summary": str(row.object_repr or ""), "error_message": message, "diff": diff,
                     "values": preview_values(source, row, state)})
    existing_numbers = {row["row_number"] for row in rows}
    for invalid in result.invalid_rows:
        if invalid.number + 1 in existing_numbers:
            continue
        message = "; ".join(f"{field}: {', '.join(map(str, errors))}" for field, errors in invalid.field_specific_errors.items())
        message = "; ".join(filter(None, [message, "; ".join(map(str, invalid.non_field_specific_errors))]))
        rows.append({"row_number": invalid.number + 1, "state": "error", "identity": "",
                     "summary": "", "error_message": message, "diff": [],
                     "values": preview_values(dict(zip(headers, dataset[invalid.number - 1])), None, "error")})
        counts["error"] += 1
    return {"summary": counts, "rows": rows,
            "global_errors": [str(item.error) for item in result.base_errors],
            "can_commit": not result.has_errors() and not result.has_validation_errors()}


class ImportBase(APIView):
    authentication_classes = [SessionAuthentication]
    permission_classes = [IsAuthenticated]

    def profile(self, request, profile):
        item = PROFILES.get(profile)
        if item is None:
            raise NotFound()
        if not item.allowed(request.user):
            raise PermissionDenied()
        return item


class ImportProfiles(ImportBase):
    def get(self, request):
        return Response({"items": [p.metadata() for p in PROFILES.values() if p.allowed(request.user)]})


class ImportTemplate(ImportBase):
    content_negotiation_class = ListExportContentNegotiation
    def get(self, request, profile):
        item = self.profile(request, profile)
        file_format = request.query_params.get("format", "xlsx")
        if file_format not in item.template_formats:
            raise ValidationError({"format": _("Unsupported template format")})
        resource = item.resource_class()
        dataset = resource.export(queryset=resource._meta.model.objects.none())
        data = dataset.export(file_format)
        response = HttpResponse(data, content_type=FORMAT_CLASSES[file_format].CONTENT_TYPE)
        response["Content-Disposition"] = f'attachment; filename="{item.key}-template.{file_format}"'
        return response


class ImportUpload(ImportBase):
    def post(self, request, profile):
        item = self.profile(request, profile)
        upload = request.FILES.get("file")
        if upload is None:
            raise ValidationError({"file": _("Choose a file")})
        if upload.size == 0:
            raise ValidationError({"file": _("File is empty")})
        if upload.size > MAX_FILE_SIZE:
            raise ValidationError({"file": _("File is too large")})
        file_format = Path(upload.name).suffix.lower().lstrip(".")
        if file_format not in item.formats:
            raise ValidationError({"file": _("Unsupported file format")})
        _clean_expired()
        identifier = str(uuid.uuid4())
        path = _temp_path(identifier)
        try:
            with path.open("xb") as target:
                for chunk in upload.chunks():
                    target.write(chunk)
                    if target.tell() > MAX_FILE_SIZE:
                        raise ValidationError({"file": _("File is too large")})
            datasets = _datasets(path.read_bytes(), file_format)
            if not datasets:
                raise ValidationError({"file": _("No sheet found")})
            if not any(sheet.headers for sheet in datasets.values()):
                raise ValidationError({"file": _("No header row found")})
        except Exception:
            path.unlink(missing_ok=True)
            raise
        first = next(iter(datasets.values()))
        return Response({"import_token": _sign(request.user, item, identifier, file_format),
                         "filename": upload.name, "size": upload.size, "format": file_format,
                         "sheets": list(datasets), "structure": _structure(item.resource_class(), first),
                         "sheet_structures": {name: _structure(item.resource_class(), sheet) for name, sheet in datasets.items()}})


class ImportPreview(ImportBase):
    def post(self, request, profile):
        item = self.profile(request, profile)
        value, path = _read_token(request.data.get("import_token"), request.user, item, previewed=False)
        dataset, sheet = _dataset(value, path, sheet=request.data.get("sheet"))
        resource = item.resource_class()
        structure = _structure(resource, dataset)
        # Missing columns are reported; the Resource remains the authority on validity.
        result = resource.import_data(_import_dataset(resource, dataset), dry_run=True, raise_errors=False,
                                      file_name=path.name, user=request.user)
        normalized = _normalize(result, dataset, resource, item)
        preview_id = str(uuid.uuid4())
        errors = {row["row_number"]: row["error_message"] for row in normalized["rows"]
                  if row["state"] == "error"}
        _preview_path(value["file"], preview_id).write_text(json.dumps(errors), encoding="utf-8")
        return Response({**normalized, "structure": structure, "sheet": sheet,
                         "import_token": _sign(request.user, item, value["file"], value["format"], sheet, True, preview_id)})


class ImportCommit(ImportBase):
    def post(self, request, profile):
        item = self.profile(request, profile)
        value, path = _read_token(request.data.get("import_token"), request.user, item, previewed=True)
        claimed = path.with_suffix(".processing")
        try:
            path.rename(claimed)
        except FileNotFoundError:
            raise ValidationError({"import_token": _("Import file has expired")})
        try:
            dataset, _ = _dataset(value, claimed)
            resource = item.resource_class()
            result = resource.import_data(_import_dataset(resource, dataset), dry_run=False, raise_errors=False,
                                          rollback_on_validation_errors=True,
                                          file_name=claimed.name, user=request.user)
        finally:
            claimed.unlink(missing_ok=True)
            for sidecar in TEMP_DIR.glob(f'{value["file"]}.*.errors'):
                sidecar.unlink(missing_ok=True)
        normalized = _normalize(result, dataset, resource, item)
        if result.has_errors() or result.has_validation_errors():
            normalized["global_errors"].append(str(_("Import rolled back because errors occurred during confirmation")))
            for row in normalized["rows"]:
                if row["state"] in ("new", "update"):
                    row["state"] = "error"
                    row["error_message"] = str(_("Import rolled back"))
            normalized["summary"] = {state: sum(row["state"] == state for row in normalized["rows"])
                                     for state in ("new", "update", "unchanged", "error")}
        else:
            if not getattr(settings, "IMPORT_EXPORT_SKIP_ADMIN_LOG", False):
                content_type = ContentType.objects.get_for_model(resource._meta.model)
                for row in result.rows:
                    action = {"new": ADDITION, "update": CHANGE}.get(row.import_type)
                    if action:
                        LogEntry.objects.log_action(user_id=request.user.pk, content_type_id=content_type.pk,
                                                    object_id=row.object_id, object_repr=row.object_repr,
                                                    action_flag=action, change_message=f"{row.import_type} through import_export")
            post_import.send(sender=None, model=resource._meta.model)
        return Response(normalized)


class ImportErrors(ImportBase):
    def get(self, request, profile):
        item = self.profile(request, profile)
        value, path = _read_token(request.query_params.get("import_token"), request.user, item, previewed=True)
        dataset, _ = _dataset(value, path)
        sidecar = _preview_path(value["file"], value.get("preview_id"))
        if not sidecar.is_file():
            raise ValidationError({"import_token": _("Preview has expired")})
        messages = {int(number): message for number, message in json.loads(sidecar.read_text(encoding="utf-8")).items()}
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow([*(dataset.headers or []), "Import error", "Import row"])
        for number, values in enumerate(dataset, start=2):
            if number in messages:
                writer.writerow([*values, messages[number], number])
        response = HttpResponse(output.getvalue(), content_type="text/csv; charset=utf-8")
        response["Content-Disposition"] = f'attachment; filename="{item.key}-errors.csv"'
        return response
