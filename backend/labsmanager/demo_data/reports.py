"""Install report templates needed by the synthetic demo accounts."""

from pathlib import Path

from django.core.files.base import ContentFile
from django.core.files.storage import default_storage

from reports.models import EmployeeWordReport, ProjectPDFReport


_BUNDLED_MEDIA = Path(__file__).resolve().parents[2] / "data" / "media"

_DEMO_REPORTS = (
    (
        EmployeeWordReport,
        "Demo Employee Report",
        "Employee report for the synthetic dataset",
        "demo_employee_report_{{datetime_SI}}.docx",
        "report/report_template/employee/employee_report.docx",
        "report/report_template/employee/demo_employee_report.docx",
    ),
    (
        ProjectPDFReport,
        "Demo Project Report",
        "Project report for the synthetic dataset",
        "demo_project_report_{{datetime_SI}}.pdf",
        "report/report_template/project/project_pdf_report.html",
        "report/report_template/project/demo_project_report.html",
    ),
)


def generate_report_templates():
    for model, name, description, filename_pattern, source_name, target_name in _DEMO_REPORTS:
        source = _BUNDLED_MEDIA / source_name
        content = source.read_bytes()

        # Each demo report owns its copy. Deleting it cannot remove an installed
        # report's template through the report model's post_delete signal.
        if default_storage.exists(target_name):
            with default_storage.open(target_name, "rb") as stored:
                if stored.read() != content:
                    default_storage.delete(target_name)
        if not default_storage.exists(target_name):
            saved_name = default_storage.save(target_name, ContentFile(content))
            if saved_name != target_name:
                raise RuntimeError(f"Could not store demo report template at {target_name}")

        report, created = model.objects.get_or_create(
            name=name,
            defaults={
                "description": description,
                "filename_pattern": filename_pattern,
                "enabled": True,
                "template": target_name,
            },
        )
        if not created:
            changed = False
            for field, value in (
                ("description", description),
                ("filename_pattern", filename_pattern),
                ("enabled", True),
                ("template", target_name),
            ):
                if getattr(report, field) != value:
                    setattr(report, field, value)
                    changed = True
            if changed:
                report.full_clean()
                report.save()
