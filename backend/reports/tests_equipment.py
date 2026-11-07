"""Equipment report registration, context isolation, and document exports."""

from copy import deepcopy
from datetime import date
from decimal import Decimal
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
from unittest.mock import patch

from django.conf import settings
from django.contrib import admin
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.contrib.contenttypes.models import ContentType
from django.test import override_settings
from django.urls import reverse
from docx import Document
from rest_framework.test import APITestCase

from equipment.models import (
    Equipment, EquipmentCategory, EquipmentExpenseLink, EquipmentGenericInfo,
    EquipmentGenericInfoType, EquipmentInstitutionInventory,
    EquipmentMaintenance, EquipmentResponsibility,
)
from expense.models import Expense
from infos.models import GenericNote
from labsmanager.tests import test_api_v1_funding
from reports.models import EquipmentPDFReport, EquipmentWordReport


class EquipmentReportTests(APITestCase):
    def setUp(self):
        test_api_v1_funding.ProjectFundingV1Tests.setUp(self)
        category = EquipmentCategory.objects.create(name="Scopes")
        self.equipment = Equipment.objects.create(name="Microscope", internal_reference="EQ-R-1", category=category)
        self.info = EquipmentGenericInfo.objects.create(
            equipment=self.equipment, info=EquipmentGenericInfoType.objects.create(name="Serial"), value="A-1",
        )
        self.responsibility = EquipmentResponsibility.objects.create(equipment=self.equipment, employee=self.employee)
        hidden_employee = get_user_model().objects.create_user(username="hidden-responsible")
        hidden_employee_record = self.employee.__class__.objects.create(first_name="Hidden", last_name="Responsible", user=hidden_employee)
        self.hidden_responsibility = EquipmentResponsibility.objects.create(equipment=self.equipment, employee=hidden_employee_record)
        self.inventory = EquipmentInstitutionInventory.objects.create(equipment=self.equipment, institution=self.institution, inventory_number="INV-1")
        self.maintenance = EquipmentMaintenance.objects.create(
            equipment=self.equipment, title="Inspection", maintenance_type="inspection", scheduled_date=date(2026, 12, 1),
        )
        expense = Expense.objects.create(fund_item=self.fund, type=self.other_type, amount=Decimal("13.00"), date=date(2026, 1, 1))
        self.link = EquipmentExpenseLink.objects.create(equipment=self.equipment, expense=expense)
        hidden_expense = Expense.objects.create(fund_item=self.hidden_fund, type=self.other_type, amount=Decimal("99.00"), date=date(2026, 1, 2))
        self.hidden_link = EquipmentExpenseLink.objects.create(equipment=self.equipment, expense=hidden_expense)
        content_type = ContentType.objects.get_for_model(Equipment)
        self.public_note = GenericNote.objects.create(content_type=content_type, object_id=self.equipment.pk, creator=self.user, name="Public", visibility="object")
        other = get_user_model().objects.create_user(username="other-note-author")
        self.private_note = GenericNote.objects.create(content_type=content_type, object_id=self.equipment.pk, creator=other, name="Private", visibility="creator")
        self.grant("view_equipment", "equipment")

    def grant(self, codename, app):
        self.user.user_permissions.add(Permission.objects.get(content_type__app_label=app, codename=codename))
        self.user = get_user_model().objects.get(pk=self.user.pk)
        self.client.force_login(self.user)

    def endpoint(self, kind):
        return reverse("api_v1:report-export", kwargs={"entity": "equipment", "pk": self.equipment.pk, "format_name": kind})

    def context(self):
        report = EquipmentWordReport(name="Test", description="", template="unused.docx")
        with patch("reports.models.registry.with_mixin", return_value=[]):
            return report.get_context(SimpleNamespace(user=self.user, GET={}), {"pk": self.equipment.pk})

    def test_registration_selection_and_template_download_permissions(self):
        self.assertIn(EquipmentWordReport, admin.site._registry)
        self.assertIn(EquipmentPDFReport, admin.site._registry)
        self.assertEqual(EquipmentWordReport.getSubdir(), "equipment")
        word = EquipmentWordReport.objects.create(name="Word", description="Template", template="word.docx")
        pdf = EquipmentPDFReport.objects.create(name="PDF", description="Template", template="pdf.html", enabled=False)
        self.assertEqual(self.client.get(self.endpoint("word")).status_code, 403)
        detail = reverse("api_v1:equipment-detail", kwargs={"pk": self.equipment.pk})
        self.assertFalse(self.client.get(detail).json()["capabilities"]["can_export_word"])
        download = reverse("download_template_report", args=["reports", "equipmentwordreport", word.pk])
        self.assertEqual(self.client.get(download).status_code, 403)
        self.grant("view_equipmentwordreport", "reports")
        self.assertTrue(self.client.get(detail).json()["capabilities"]["can_export_word"])
        self.assertFalse(self.client.get(detail).json()["capabilities"]["can_export_pdf"])
        self.assertEqual(self.client.get(self.endpoint("word")).json()["templates"], [{"id": word.pk, "name": "Word"}])
        self.assertEqual(self.client.get(self.endpoint("pdf")).status_code, 403)
        self.grant("view_equipmentpdfreport", "reports")
        self.assertEqual(self.client.get(self.endpoint("pdf")).json()["templates"], [])
        self.assertEqual(self.client.post(self.endpoint("pdf"), {"template_id": pdf.pk}, format="json").status_code, 404)
        self.assertEqual(self.client.post(self.endpoint("word"), {"template_id": 999999}, format="json").status_code, 404)
        self.assertEqual(self.client.post(self.endpoint("word"), {"template_id": word.pk, "start_date": "2026-01-01"}, format="json").status_code, 400)

    def test_context_respects_each_related_permission(self):
        context = self.context()
        self.assertEqual(context["equipment"], self.equipment)
        self.assertEqual(list(context["info"]), [])
        self.assertEqual(list(context["responsibility"]), [])
        self.assertEqual(list(context["institution"]), [])
        self.assertEqual(list(context["maintenance"]), [])
        self.assertEqual(list(context["expense"]), [])
        self.assertEqual(list(context["notes"]), [self.public_note])
        self.assertEqual(context["user"], self.user)
        for code, app in (
            ("view_equipmentgenericinfo", "equipment"), ("view_equipmentresponsibility", "equipment"),
            ("view_equipmentinstitutioninventory", "equipment"), ("view_institution", "project"),
            ("view_equipmentmaintenance", "equipment"), ("view_equipmentexpenselink", "equipment"),
        ):
            self.grant(code, app)
        context = self.context()
        self.assertEqual(list(context["info"]), [self.info])
        self.assertEqual(list(context["responsibility"]), [self.responsibility])
        self.assertEqual(list(context["institution"]), [self.inventory])
        self.assertEqual(list(context["maintenance"]), [self.maintenance])
        self.assertEqual(list(context["expense"]), [self.link.expense])
        self.assertNotIn(self.private_note, context["notes"])

    def test_real_word_pdf_export_and_filename(self):
        self.grant("view_equipmentwordreport", "reports")
        self.grant("view_equipmentpdfreport", "reports")
        with TemporaryDirectory() as media_root:
            directory = Path(media_root, "report", "report_template", "equipment")
            directory.mkdir(parents=True)
            document = Document()
            document.add_paragraph("{{ equipment.name }}")
            document.save(directory / "minimal.docx")
            (directory / "minimal.html").write_text("<html><body>{{ equipment.name }}</body></html>", encoding="utf-8")
            templates = deepcopy(settings.TEMPLATES)
            templates[0]["DIRS"].insert(0, directory)
            with override_settings(MEDIA_ROOT=Path(media_root), TEMPLATES=templates), patch("reports.models.settings.MEDIA_ROOT", Path(media_root)), patch("reports.models.registry.with_mixin", return_value=[]):
                word = EquipmentWordReport.objects.create(name="Word", description="Minimal", template="report/report_template/equipment/minimal.docx", filename_pattern="equipment-{{ equipment.pk }}.docx")
                pdf = EquipmentPDFReport.objects.create(name="PDF", description="Minimal", template="report/report_template/equipment/minimal.html", filename_pattern="equipment-{{ equipment.pk }}.pdf")
                template_download = self.client.get(reverse("download_template_report", args=["reports", "equipmentwordreport", word.pk]))
                self.assertEqual(template_download.status_code, 200)
                self.assertTrue(b"".join(template_download.streaming_content).startswith(b"PK"))
                word_response = self.client.post(self.endpoint("word"), {"template_id": word.pk}, format="json")
                pdf_response = self.client.post(self.endpoint("pdf"), {"template_id": pdf.pk}, format="json")
                self.assertEqual(word_response.status_code, 200)
                self.assertIn(f"equipment-{self.equipment.pk}.docx", word_response["Content-Disposition"])
                self.assertTrue(b"".join(word_response.streaming_content).startswith(b"PK"))
                self.assertEqual(pdf_response.status_code, 200)
                self.assertIn(f"equipment-{self.equipment.pk}.pdf", pdf_response["Content-Disposition"])
                self.assertTrue(pdf_response.content.startswith(b"%PDF"))

    def test_no_export_without_equipment_visibility(self):
        self.grant("view_equipmentwordreport", "reports")
        self.user.user_permissions.remove(Permission.objects.get(content_type__app_label="equipment", codename="view_equipment"))
        self.user = get_user_model().objects.get(pk=self.user.pk)
        self.client.force_login(self.user)
        self.assertEqual(self.client.get(self.endpoint("word")).status_code, 404)
