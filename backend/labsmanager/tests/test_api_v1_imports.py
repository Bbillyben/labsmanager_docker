"""Import Hub contracts against the historical Resources."""

import csv
from io import StringIO
from unittest.mock import patch

import tablib
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.core.exceptions import ImproperlyConfigured
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse
from rest_framework.test import APITestCase

from expense.models import Expense
from expense.models import Expense_point
from expense.resources import ExpensePointResource, ExpenseResource
from settings.models import LMProjectSetting
from staff.ressources import EmployeeAdminResource
from staff.models import Employee

class ImportHubTests(APITestCase):
    def setUp(self):
        from .test_api_v1_funding import ProjectFundingV1Tests
        ProjectFundingV1Tests.setUp(self)
        LMProjectSetting.set_setting("EXPENSE_CALCULATION", "e", change_user=None, project=self.project)
        self.user.user_permissions.add(Permission.objects.get(content_type__app_label="common", codename="import"))
        self.user = get_user_model().objects.get(pk=self.user.pk)
        self.client.force_login(self.user)

    def url(self, action, profile="expense"):
        return reverse(f"api_v1:import-{action}", kwargs={"profile": profile} if action != "profiles" else {})

    def data(self, entries):
        fields = list(ExpenseResource().export(queryset=Expense.objects.none()).headers)
        output = StringIO()
        writer = csv.DictWriter(output, fieldnames=fields)
        writer.writeheader()
        for entry in entries:
            writer.writerow({"Expense Id": entry[0], "Description": entry[1], "type": self.type.short_name,
                             "Amount": entry[2], "Ref": self.fund.ref, "date": "2026-03-01"})
        return output.getvalue().encode()

    def upload(self, data=None, name="expenses.csv"):
        file = SimpleUploadedFile(name, data or self.data([("IMP-1", "First", "10")]))
        response = self.client.post(self.url("upload"), {"file": file}, format="multipart")
        self.assertEqual(response.status_code, 200, response.data)
        return response.data

    def test_registry_permissions_and_templates(self):
        response = self.client.get(reverse("api_v1:import-profiles"))
        self.assertEqual({item["key"] for item in response.data["items"]},
                         {"expense", "employee", "expense-timepoint"})
        from importlib import import_module
        profiles = import_module("import.profiles").PROFILES
        self.assertIs(profiles["expense"].resource_class, ExpenseResource)
        self.assertIs(profiles["employee"].resource_class, EmployeeAdminResource)
        self.assertIs(profiles["expense-timepoint"].resource_class, ExpensePointResource)
        columns = ("expense_id", "desc", "type", "amount", "project", "fund",
                   "funder", "institution", "date")
        self.assertEqual(profiles["expense"].preview_columns, columns)
        resource = ExpenseResource()
        self.assertIn("date", resource.fields)
        self.assertTrue(all(name in resource.fields for name in columns))
        metadata = {item["key"]: item for item in response.data["items"]}
        self.assertEqual(metadata["expense"]["preview_columns"], [
            {"key": name, "label": str(resource.fields[name].column_name)} for name in columns
        ])
        self.assertEqual(metadata["employee"]["preview_columns"], [])
        self.assertEqual(metadata["expense-timepoint"]["preview_columns"], [])
        from dataclasses import replace
        with self.assertRaisesMessage(ImproperlyConfigured, "Import profile 'expense' references unknown preview field 'foo'"):
            replace(profiles["expense"], preview_columns=("foo",)).metadata()
        for file_format in ("csv", "xlsx"):
            response = self.client.get(self.url("template"), {"format": file_format})
            self.assertEqual(response.status_code, 200)
            dataset = tablib.import_set(response.content.decode() if file_format == "csv" else response.content, format=file_format)
            self.assertEqual(dataset.headers, ExpenseResource().export(queryset=Expense.objects.none()).headers)
            self.assertEqual(len(dataset), 0)
        other = get_user_model().objects.create_user("no-import")
        self.client.force_login(other)
        self.assertEqual(self.client.get(reverse("api_v1:import-profiles")).data["items"], [])
        self.assertEqual(self.client.get(self.url("template")).status_code, 403)

    def test_preview_commit_and_error_file(self):
        uploaded = self.upload(self.data([("IMP-1", "First", "10"), ("IMP-2", "Second", "20")]))
        preview = self.client.post(self.url("preview"), {"import_token": uploaded["import_token"], "sheet": ""}, format="json")
        self.assertEqual(preview.status_code, 200, preview.data)
        self.assertEqual(preview.data["summary"]["new"], 2)
        values = preview.data["rows"][0]["values"]
        self.assertEqual(set(values), {"expense_id", "desc", "type", "amount", "project",
                                       "fund", "funder", "institution", "date"})
        self.assertEqual(values["expense_id"], "IMP-1")
        self.assertEqual(values["desc"], "First")
        self.assertEqual(values["type"], self.type.short_name)
        self.assertEqual(values["amount"], "10")
        self.assertEqual(values["project"], self.project.name)
        self.assertEqual(values["fund"], self.fund.ref)
        self.assertEqual(values["funder"], self.fund.funder.short_name)
        self.assertEqual(values["institution"], self.fund.institution.short_name)
        self.assertEqual(values["date"], "2026-03-01")
        self.assertEqual(Expense.objects.filter(expense_id__startswith="IMP-").count(), 0)
        token = preview.data["import_token"]
        final = self.client.post(self.url("commit"), {"import_token": token}, format="json").data
        self.assertEqual(final["summary"]["new"], 2)
        self.assertEqual(final["rows"][0]["values"], values)
        self.assertEqual(Expense.objects.filter(expense_id__startswith="IMP-").count(), 2)
        self.assertEqual(self.client.post(self.url("commit"), {"import_token": token}, format="json").status_code, 400)

    def test_excel_sheets_and_token_scope(self):
        fields = ExpenseResource().export(queryset=Expense.objects.none()).headers
        book = tablib.Databook([tablib.Dataset(title="A", headers=fields), tablib.Dataset(title="B", headers=fields)])
        uploaded = self.upload(book.export("xlsx"), "expenses.xlsx")
        self.assertEqual(uploaded["sheets"], ["A", "B"])
        self.assertEqual(self.client.post(self.url("preview"), {"import_token": uploaded["import_token"], "sheet": "Z"}, format="json").status_code, 400)
        preview = self.client.post(self.url("preview"), {"import_token": uploaded["import_token"], "sheet": "B"}, format="json")
        self.assertEqual(preview.status_code, 200, preview.data)
        self.assertEqual(preview.data["sheet"], "B")
        with patch("import.api_v1.TOKEN_AGE", -1):
            self.assertEqual(self.client.post(self.url("commit"), {"import_token": preview.data["import_token"]}, format="json").status_code, 400)
        self.assertEqual(self.client.post(self.url("commit", "employee"), {"import_token": preview.data["import_token"]}, format="json").status_code, 403)
        other = get_user_model().objects.create_user("other-import")
        other.user_permissions.add(Permission.objects.get(content_type__app_label="common", codename="import"))
        self.client.force_login(other)
        self.assertEqual(self.client.post(self.url("commit"), {"import_token": preview.data["import_token"]}, format="json").status_code, 403)

    def test_invalid_fund_keeps_the_raw_reference_in_preview(self):
        data = self.data([("IMP-BAD", "Unknown fund", "10")]).replace(
            self.fund.ref.encode(), b"ANR-UNKNOWN"
        )
        uploaded = self.upload(data)
        preview = self.client.post(self.url("preview"), {
            "import_token": uploaded["import_token"], "sheet": "",
        }, format="json")
        self.assertEqual(preview.status_code, 200, preview.data)
        self.assertEqual(preview.data["rows"][0]["state"], "error")
        self.assertEqual(preview.data["rows"][0]["values"]["fund"], "ANR-UNKNOWN")
        self.assertEqual(preview.data["rows"][0]["values"]["desc"], "Unknown fund")

    def test_update_skip_error_download_and_partial_commit(self):
        first = self.upload()
        preview = self.client.post(self.url("preview"), {"import_token": first["import_token"], "sheet": ""}, format="json").data
        self.client.post(self.url("commit"), {"import_token": preview["import_token"]}, format="json")
        data = self.data([("IMP-1", "First", "10"), ("IMP-2", "Second", "20"), ("IMP-3", "Third", "30")])
        data = data.replace(b"IMP-3,Third,HR", b"IMP-3,Third,UNKNOWN")
        second = self.upload(data)
        preview = self.client.post(self.url("preview"), {"import_token": second["import_token"], "sheet": ""}, format="json")
        self.assertEqual(preview.status_code, 200, preview.data)
        # ExpenseResource reports this same-value row as UPDATE under its
        # existing SkipSameValueRessource comparison; retain that authority.
        self.assertEqual(preview.data["summary"], {"new": 1, "update": 1, "unchanged": 0, "error": 1})
        self.assertTrue(preview.data["rows"][0]["diff"])
        self.assertEqual(preview.data["rows"][0]["values"]["project"], self.project.name)
        self.assertEqual(preview.data["rows"][0]["values"]["date"], "2026-03-01")
        self.assertTrue(preview.data["can_commit"])
        self.assertTrue(preview.data["rows"][-1]["error_message"])
        self.assertEqual(preview.data["rows"][-1]["values"]["type"], "UNKNOWN")
        self.assertEqual(preview.data["rows"][-1]["values"]["fund"], self.fund.ref)
        with patch.object(ExpenseResource, "import_data", side_effect=AssertionError("Do not rerun preview")):
            errors = self.client.get(self.url("errors"), {"import_token": preview.data["import_token"]})
        self.assertEqual(errors.status_code, 200)
        self.assertEqual(len(list(csv.reader(StringIO(errors.content.decode())))), 2)
        final = self.client.post(self.url("commit"), {"import_token": preview.data["import_token"]}, format="json")
        self.assertEqual(final.status_code, 200, final.data)
        self.assertEqual(final.data["summary"], preview.data["summary"])
        self.assertTrue(Expense.objects.filter(expense_id="IMP-2").exists())
        self.assertFalse(Expense.objects.filter(expense_id="IMP-3").exists())

    def test_employee_and_timepoint_use_the_same_preview_engine(self):
        cases = (
            ("employee", EmployeeAdminResource, Employee, {"First Name": "New", "Last Name": "Person", "Email": "new@example.org", "is_active": "True"}),
            ("expense-timepoint", ExpensePointResource, Expense_point,
             {"Ref": self.fund.ref, "type": self.type.short_name, "Entry Date": "2026-03-01",
              "Value Date": "2026-03-01", "expense": "-12"}),
        )
        for profile, resource_class, model, values in cases:
            with self.subTest(profile=profile):
                if profile == "expense-timepoint":
                    LMProjectSetting.set_setting("EXPENSE_CALCULATION", "s", change_user=None, project=self.project)
                headers = resource_class().export(queryset=model.objects.none()).headers
                output = StringIO()
                writer = csv.DictWriter(output, fieldnames=headers)
                writer.writeheader()
                writer.writerow(values)
                count_before = model.objects.count()
                uploaded = self.client.post(
                    self.url("upload", profile), {"file": SimpleUploadedFile(f"{profile}.csv", output.getvalue().encode())}, format="multipart"
                ).data
                preview = self.client.post(self.url("preview", profile), {"import_token": uploaded["import_token"], "sheet": ""}, format="json")
                self.assertEqual(preview.status_code, 200, preview.data)
                self.assertEqual(preview.data["summary"]["new" if profile == "employee" else "update"], 1, preview.data)
                if profile == "expense-timepoint":
                    self.assertTrue(any(item["field"] == "Entry Date" for item in preview.data["rows"][0]["diff"]))
                self.assertEqual(model.objects.count(), count_before)
