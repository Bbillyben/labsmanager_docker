"""Import Hub contracts against the historical Resources."""

import csv
from io import StringIO
from unittest.mock import patch

import tablib
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.core.exceptions import ImproperlyConfigured
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import SimpleTestCase
from django.urls import reverse
from rest_framework.test import APITestCase

from expense.models import Expense
from expense.models import Expense_point
from expense.resources import ExpensePointResource, ExpenseResource
from settings.models import LMProjectSetting
from staff.ressources import EmployeeAdminResource
from staff.models import Employee
from plugin.base.ImportMixin import ImportMixin


class DemoImportPlugin(ImportMixin):
    human_name = "Demo Import"
    import_method = [
        {"id": "expenses", "label": "Raw expenses", "resource": "ExpenseResource",
         "handler": "transform_expenses", "columns": {"Code": [" ID "], "Amount": ["Total"]}},
        {"id": "expenses-alt", "label": "Other expenses", "resource": "ExpenseResource",
         "handler": "transform_expenses", "columns": {"Code": [], "Amount": []}},
    ]

    def __init__(self, slug="demo", active=True):
        self.slug, self.active = slug, active
        super().__init__()

    def add_mixin(self, key, enabled, cls):
        self.mixin_key = key

    def mixin_enabled(self, key):
        return key == self.mixin_key

    def is_active(self):
        return self.active

    def transform_expenses(self, dataset, current_import_methode):
        headers = ExpenseResource().export(queryset=Expense.objects.none()).headers
        rows = []
        for row in dataset.dict:
            values = {"Expense Id": row["Code"], "Description": "Plugin import",
                      "type": self.expense_type, "Amount": row["Amount"],
                      "Ref": self.fund_ref, "date": "2026-03-01"}
            rows.append([values.get(header, "") for header in headers])
        return tablib.Dataset(*rows, headers=headers)


class ImportMixinTests(SimpleTestCase):
    def setUp(self):
        self.plugin = DemoImportPlugin()
        self.method = self.plugin.import_method[0]

    def test_template_aliases_extra_columns_and_normalization(self):
        self.assertEqual(self.plugin.get_import_template(self.method).headers, ["Code", "Amount"])
        source = tablib.Dataset(["E-1", "10", "ignore"], headers=[" id ", " TOTAL ", "Extra"])
        self.assertIs(self.plugin.prepare_dataset(source, self.method, {"header_row": 1}), source)
        report = self.plugin.check_eligibility(source, self.method, {"header_row": 2})
        self.assertTrue(report["eligible"])
        self.assertEqual(report["aliases_used"], {"Code": " id ", "Amount": " TOTAL "})
        self.assertEqual(report["extra"], ["Extra"])
        normalized = self.plugin.normalize_columns(source, self.method)
        self.assertEqual(normalized.headers, ["Code", "Amount"])
        self.assertEqual(list(normalized[0]), ["E-1", "10"])

    def test_missing_duplicate_and_conflicting_aliases_block(self):
        missing = self.plugin.check_eligibility(tablib.Dataset(["E-1"], headers=["Code"]), self.method)
        self.assertEqual(missing["missing"], ["Amount"])
        duplicate = self.plugin.check_eligibility(tablib.Dataset(["E-1", "E-2", "10"],
                                                                   headers=["Code", "ID", "Amount"]), self.method)
        self.assertFalse(duplicate["eligible"])
        self.assertTrue(duplicate["ambiguities"])
        with self.assertRaises(ValueError):
            self.plugin.normalize_columns(tablib.Dataset(["E-1", "E-2", "10"],
                                                                  headers=["Code", "ID", "Amount"]), self.method)
        conflicting = {**self.method, "columns": {"Code": ["Same"], "Amount": ["same"]}}
        self.assertFalse(self.plugin.check_eligibility(tablib.Dataset(["x", "10"], headers=["Code", "Amount"]), conflicting)["eligible"])

    def test_plugin_can_extend_generic_eligibility(self):
        class Extended(DemoImportPlugin):
            def check_eligibility(self, dataset, current_import_methode, option_data=None):
                report = super().check_eligibility(dataset, current_import_methode, option_data)
                report["warnings"].append("Custom check")
                return report
        report = Extended().check_eligibility(tablib.Dataset(["E-1", "10"], headers=["Code", "Amount"]), self.method)
        self.assertEqual(report["warnings"], ["Custom check"])

    def test_registry_exposes_only_active_import_plugins(self):
        from plugin.registry import registry
        active, inactive = DemoImportPlugin("active"), DemoImportPlugin("inactive", active=False)
        with patch.object(registry, "check_reload"), patch.object(registry, "plugins", {"active": active, "inactive": inactive}):
            self.assertEqual(registry.with_mixin("importmixin"), [active])

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

    def test_plugin_methods_template_preview_and_confirm_saved_dataset(self):
        plugin = DemoImportPlugin()
        plugin.expense_type, plugin.fund_ref = self.type.short_name, self.fund.ref
        with patch("plugin.registry.registry.with_mixin", return_value=[plugin]):
            profiles = self.client.get(self.url("profiles")).data["items"]
            self.assertEqual({p["key"] for p in profiles if p.get("plugin_import")},
                             {"plugin:demo:expenses", "plugin:demo:expenses-alt"})
            template = self.client.get(self.url("template", "plugin:demo:expenses"))
            self.assertEqual(template.status_code, 200)
            self.assertEqual(tablib.import_set(template.content, format="xlsx").headers, ["Code", "Amount"])
            source = b"ignore,ignore\n ID , Total \nPLUGIN-1,10\n"
            uploaded = self.client.post(self.url("upload", "plugin:demo:expenses"),
                                        {"file": SimpleUploadedFile("raw.csv", source)}, format="multipart")
            self.assertEqual(uploaded.status_code, 200, uploaded.data)
            self.assertFalse(uploaded.data["structure"]["eligible"])
            token = uploaded.data["import_token"]
            with patch("plugin.registry.registry.with_mixin", return_value=[]):
                self.assertEqual(self.client.post(self.url("preview", "plugin:demo:expenses"),
                                                  {"import_token": token, "sheet": ""}, format="json").status_code, 404)
            invalid = self.client.post(self.url("preview", "plugin:demo:expenses"),
                                       {"import_token": token, "sheet": ""}, format="json")
            self.assertFalse(invalid.data["can_commit"])
            self.assertEqual(Expense.objects.filter(expense_id="PLUGIN-1").count(), 0)
            preview = self.client.post(self.url("preview", "plugin:demo:expenses"),
                                       {"import_token": token, "sheet": "", "header_row": 2}, format="json")
            self.assertEqual(preview.status_code, 200, preview.data)
            self.assertTrue(preview.data["structure"]["eligible"])
            self.assertEqual(preview.data["structure"]["aliases_used"], {"Code": " ID ", "Amount": " Total "})
            self.assertEqual(preview.data["summary"]["new"], 1)
            self.assertEqual(Expense.objects.filter(expense_id="PLUGIN-1").count(), 0)
            with patch.object(plugin, "transform_expenses", side_effect=AssertionError("Handler must not rerun")):
                final = self.client.post(self.url("commit", "plugin:demo:expenses"),
                                         {"import_token": preview.data["import_token"]}, format="json")
            self.assertEqual(final.status_code, 200, final.data)
            self.assertEqual(final.data["rows"][0]["values"], preview.data["rows"][0]["values"])
            self.assertEqual(Expense.objects.filter(expense_id="PLUGIN-1").count(), 1)

    def test_plugin_preparation_is_shared_by_eligibility_normalization_and_handler(self):
        class PreparedPlugin(DemoImportPlugin):
            def __init__(self):
                super().__init__()
                self.preparations = []
                self.checked = []
                self.normalized = []
                self.handled = []

            def prepare_dataset(self, dataset, current_import_methode, option_data=None):
                self.preparations.append(option_data)
                rows = [list(dataset.headers), *[list(row) for row in dataset]]
                header = next(index for index, row in enumerate(rows)
                              if [self._header(value) for value in row] == ["id", "total"])
                return tablib.Dataset(*[row for row in rows[header + 1:] if any(value is not None and str(value).strip() for value in row)],
                                      headers=rows[header])

            def check_eligibility(self, dataset, current_import_methode, option_data=None):
                self.checked.append((list(dataset.headers), option_data))
                return super().check_eligibility(dataset, current_import_methode, option_data)

            def normalize_columns(self, dataset, current_import_methode):
                self.normalized.append(list(dataset.headers))
                return super().normalize_columns(dataset, current_import_methode)

            def transform_expenses(self, dataset, current_import_methode):
                self.handled.append((list(dataset.headers), list(dataset[0])))
                return super().transform_expenses(dataset, current_import_methode)

        plugin = PreparedPlugin()
        plugin.expense_type, plugin.fund_ref = self.type.short_name, self.fund.ref
        raw = tablib.Dataset(headers=["", ""])
        for row in (["", ""], [" ID ", " Total "], ["", ""], ["PREPARED-1", "10"]):
            raw.append(row)
        with patch("plugin.registry.registry.with_mixin", return_value=[plugin]):
            uploaded = self.client.post(self.url("upload", "plugin:demo:expenses"),
                                        {"file": SimpleUploadedFile("raw.xlsx", raw.export("xlsx"))}, format="multipart")
            self.assertEqual(uploaded.status_code, 200, uploaded.data)
            self.assertTrue(uploaded.data["structure"]["eligible"])
            self.assertEqual(uploaded.data["structure"]["rows"], 1)
            sheet = uploaded.data["sheets"][0]
            preview = self.client.post(self.url("preview", "plugin:demo:expenses"),
                                       {"import_token": uploaded.data["import_token"], "sheet": sheet}, format="json")
            self.assertEqual(preview.status_code, 200, preview.data)
            self.assertEqual(preview.data["summary"]["new"], 1)
            self.assertEqual(len(plugin.preparations), 2)  # One parsed Dataset per upload and preview request.
            self.assertEqual(plugin.checked[-1], ([" ID ", " Total "], {"sheet": sheet, "header_row": 1}))
            self.assertEqual(plugin.normalized, [[" ID ", " Total "]])
            self.assertEqual(plugin.handled, [(["Code", "Amount"], ["PREPARED-1", "10"])])
            with patch.object(plugin, "prepare_dataset", side_effect=AssertionError("Do not prepare again")), \
                    patch.object(plugin, "transform_expenses", side_effect=AssertionError("Do not transform again")):
                final = self.client.post(self.url("commit", "plugin:demo:expenses"),
                                         {"import_token": preview.data["import_token"]}, format="json")
            self.assertEqual(final.status_code, 200, final.data)
            self.assertEqual(final.data["rows"][0]["values"], preview.data["rows"][0]["values"])
            self.assertEqual(Expense.objects.filter(expense_id="PREPARED-1").count(), 1)

    def test_plugin_registry_scope_resource_and_permissions(self):
        first, second = DemoImportPlugin("one"), DemoImportPlugin("two")
        first.expense_type = second.expense_type = self.type.short_name
        first.fund_ref = second.fund_ref = self.fund.ref
        with patch("plugin.registry.registry.with_mixin", return_value=[first, second]):
            profiles = self.client.get(self.url("profiles")).data["items"]
            self.assertIn("plugin:one:expenses", {item["key"] for item in profiles})
            self.assertIn("plugin:two:expenses", {item["key"] for item in profiles})
            self.assertEqual({item["plugin_name"] for item in profiles if item.get("plugin_import")}, {"Demo Import"})
            other = get_user_model().objects.create_user("no-plugin-import")
            self.client.force_login(other)
            self.assertFalse(any(item.get("plugin_import") for item in self.client.get(self.url("profiles")).data["items"]))
            self.assertEqual(self.client.get(self.url("template", "plugin:one:expenses")).status_code, 403)
        self.client.force_login(self.user)
        with patch("plugin.registry.registry.with_mixin", return_value=[]):
            self.assertEqual(self.client.get(self.url("template", "plugin:one:expenses")).status_code, 404)
        first.import_method = [{**first.import_method[0], "resource": "UnknownResource"}]
        with patch("plugin.registry.registry.with_mixin", return_value=[first]):
            keys = {item["key"] for item in self.client.get(self.url("profiles")).data["items"]}
            self.assertNotIn("plugin:one:expenses", keys)
            self.assertIn("expense", keys)
        first.import_method = [{**first.import_method[0], "resource": "ExpenseResource", "handler": "unknown_handler"}]
        with patch("plugin.registry.registry.with_mixin", return_value=[first]):
            self.assertNotIn("plugin:one:expenses", {item["key"] for item in self.client.get(self.url("profiles")).data["items"]})

    def test_same_method_id_in_two_plugins_keeps_each_import_separate(self):
        first, second = DemoImportPlugin("one"), DemoImportPlugin("two")
        first.human_name, second.human_name = "First import", "Second import"
        for plugin in (first, second):
            plugin.expense_type, plugin.fund_ref = self.type.short_name, self.fund.ref
        first.get_import_template = lambda method: tablib.Dataset(headers=["First template"])
        second.get_import_template = lambda method: tablib.Dataset(headers=["Second template"])
        with patch("plugin.registry.registry.with_mixin", return_value=[first, second]), \
                patch.object(first, "transform_expenses", wraps=first.transform_expenses) as first_handler, \
                patch.object(second, "transform_expenses", wraps=second.transform_expenses) as second_handler:
            items = {item["key"]: item for item in self.client.get(self.url("profiles")).data["items"]}
            self.assertEqual(items["plugin:one:expenses"]["plugin_name"], "First import")
            self.assertEqual(items["plugin:two:expenses"]["plugin_name"], "Second import")
            self.assertEqual(tablib.import_set(self.client.get(self.url("template", "plugin:one:expenses")).content, format="xlsx").headers,
                             ["First template"])
            self.assertEqual(tablib.import_set(self.client.get(self.url("template", "plugin:two:expenses")).content, format="xlsx").headers,
                             ["Second template"])
            previews = {}
            for slug in ("one", "two"):
                key = f"plugin:{slug}:expenses"
                raw = f"Code,Amount\n{slug.upper()}-1,10\n".encode()
                upload = self.client.post(self.url("upload", key),
                                          {"file": SimpleUploadedFile(f"{slug}.csv", raw)}, format="multipart")
                self.assertEqual(upload.status_code, 200, upload.data)
                previews[slug] = self.client.post(self.url("preview", key),
                                                  {"import_token": upload.data["import_token"], "sheet": ""}, format="json")
                self.assertEqual(previews[slug].status_code, 200, previews[slug].data)
                other = "two" if slug == "one" else "one"
                self.assertEqual(self.client.post(self.url("preview", f"plugin:{other}:expenses"),
                                                  {"import_token": upload.data["import_token"], "sheet": ""}, format="json").status_code, 403)
            first_handler.assert_called_once()
            second_handler.assert_called_once()
            self.assertEqual(self.client.post(self.url("commit", "plugin:two:expenses"),
                                              {"import_token": previews["one"].data["import_token"]}, format="json").status_code, 403)
            for slug in ("one", "two"):
                result = self.client.post(self.url("commit", f"plugin:{slug}:expenses"),
                                          {"import_token": previews[slug].data["import_token"]}, format="json")
                self.assertEqual(result.status_code, 200, result.data)
                self.assertEqual(result.data["rows"][0]["values"], previews[slug].data["rows"][0]["values"])
                self.assertEqual(Expense.objects.filter(expense_id=f"{slug.upper()}-1").count(), 1)
        with patch("plugin.registry.registry.with_mixin", return_value=[second]):
            keys = {item["key"] for item in self.client.get(self.url("profiles")).data["items"]}
            self.assertNotIn("plugin:one:expenses", keys)
            self.assertIn("plugin:two:expenses", keys)
            self.assertEqual(self.client.get(self.url("template", "plugin:one:expenses")).status_code, 404)
            self.assertEqual(self.client.get(self.url("template", "plugin:two:expenses")).status_code, 200)

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
