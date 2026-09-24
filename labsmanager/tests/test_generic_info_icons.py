"""Icon data preservation and bounded legacy compatibility."""
from importlib import import_module
from django.contrib import admin
from django.contrib.auth import get_user_model
from django.db import connection
from django.db.migrations.executor import MigrationExecutor
from django.template.loader import render_to_string
from django.test import RequestFactory, TestCase
from faicon.fields import FAIconField
from faicon.widgets import Icon
from labsmanager.serializers import EmployeeInfoTypeIconSerialize, ProjectInfoTypeIconSerialize
from staff.forms import GenericInfoTypeForm
from staff.models import Employee, GenericInfo, GenericInfoType
from project.models import GenericInfoTypeProject
from settings.views import SettingList_GenericInfo

migration = import_module("staff.migrations.0014_genericinfotype_icon_lucide")


class GenericInfoIconTests(TestCase):
    def test_mapping_unknown_null_empty_and_irreversibility(self):
        values = [
            "style:fas,icon:id-badge", "style:far,icon:id-badge",
            "style:far,icon:address-book", "style:fab,icon:searchengin",
            "style:fas,icon:table-columns", "style:fas,icon:user-doctor",
            "style:fas,icon:unknown", "unrecognized", "", None,
        ]
        expected = ["Badge", "Badge", "Contact", "Search", "Columns3", "Stethoscope",
                    "style:fas,icon:unknown", "unrecognized", "", None]
        for index, value in enumerate(values):
            GenericInfoType.objects.create(name=f"type-{index}", icon=value)
        executor = MigrationExecutor(connection)
        historical_apps = executor.loader.project_state([("staff", "0014_genericinfotype_icon_lucide")]).apps
        with connection.schema_editor() as editor:
            migration.convert_icons(historical_apps, editor)
        for index, value in enumerate(expected):
            self.assertEqual(GenericInfoType.objects.get(name=f"type-{index}").icon, value)
        self.assertFalse(migration.Migration.operations[-1].reversible)
        with connection.schema_editor() as editor:
            migration.convert_icons(historical_apps, editor)
        self.assertEqual(GenericInfoType.objects.get(name="type-0").icon, "Badge")

    def test_employee_legacy_and_project_faicon(self):
        user = get_user_model().objects.create_user(username="legacy-icons")
        employee = Employee.objects.create(first_name="Icon", last_name="Owner", user=user)
        info_type = GenericInfoType.objects.create(name="Badge", icon="Badge")
        info = GenericInfo.objects.create(employee=employee, info=info_type, value="123")
        self.assertEqual(EmployeeInfoTypeIconSerialize(info_type).data["icon_val"], "Badge")
        form = GenericInfoTypeForm(instance=info_type)
        self.assertNotIn("faicon", str(form.media))
        self.assertIn("Badge", form.as_p())
        form = GenericInfoTypeForm(data={"name": "Another", "icon": "Contact"}, request=RequestFactory().post("/"))
        self.assertTrue(form.is_valid(), form.errors)
        self.assertEqual(form.save().icon, "Contact")
        self.assertEqual(admin.site._registry[GenericInfoType].list_display, ("name", "icon"))
        html = render_to_string("employee/employee_info_table.html", {"user": user, "employee": employee, "infoEmployee": [info]})
        self.assertIn("Badge", html)
        request = RequestFactory().get("/")
        request.user = user
        self.assertEqual(SettingList_GenericInfo.as_view()(request).status_code, 200)
        project_type = GenericInfoTypeProject.objects.create(name="Project icon", icon="style:fas,icon:id-badge")
        project_type.refresh_from_db()
        self.assertIsInstance(GenericInfoTypeProject._meta.get_field("icon"), FAIconField)
        self.assertIsInstance(project_type.icon, Icon)
        self.assertEqual(ProjectInfoTypeIconSerialize(project_type).data["icon_val"], {"style": "fas", "icon": "id-badge"})
        self.assertIn("fa-id-badge", str(admin.site._registry[GenericInfoTypeProject].get_icon(project_type)))
