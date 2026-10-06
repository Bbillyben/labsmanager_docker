"""R2.24a icon conversion for both concrete information type tables."""

from importlib import import_module

from django.db import connection
from django.db.migrations.executor import MigrationExecutor
from django.test import TestCase

from infos.models import ContactInfoType, OrganizationInfosType


migration = import_module("infos.migrations.0017_organization_contact_icons_lucide")


class OrganizationInfoIconTests(TestCase):
    def convert(self):
        historical_apps = MigrationExecutor(connection).loader.project_state([
            ("infos", "0017_organization_contact_icons_lucide")
        ]).apps
        with connection.schema_editor() as editor:
            migration.convert_icons(historical_apps, editor)

    def test_mapping_both_models_and_preserving_null_and_blank(self):
        for model in (OrganizationInfosType, ContactInfoType):
            for index, old_icon in enumerate(migration.ICON_MAPPING):
                model.objects.create(name=f"{model.__name__}-{index}", icon=old_icon)
            model.objects.create(name=f"{model.__name__}-null", icon=None)
            model.objects.create(name=f"{model.__name__}-blank", icon="")
        ContactInfoType.objects.create(name="aze", icon="style:fab,icon:adn")

        self.convert()
        for model in (OrganizationInfosType, ContactInfoType):
            for index, expected in enumerate(migration.ICON_MAPPING.values()):
                self.assertEqual(model.objects.get(name=f"{model.__name__}-{index}").icon, expected)
            self.assertIsNone(model.objects.get(name=f"{model.__name__}-null").icon)
            self.assertEqual(model.objects.get(name=f"{model.__name__}-blank").icon, "")
            self.assertEqual(model._meta.get_field("icon").get_internal_type(), "CharField")
        self.convert()  # Already converted Lucide names remain unchanged.
        self.assertEqual(ContactInfoType.objects.get(name="ContactInfoType-10").icon, "Phone")
        self.assertEqual(ContactInfoType.objects.get(name="aze").icon, "Dna")

    def test_unknown_icon_stops_both_tables_before_conversion(self):
        organization = OrganizationInfosType.objects.create(name="Known", icon="style:fas,icon:phone")
        ContactInfoType.objects.create(name="Unknown", icon="style:fas,icon:unmapped")
        with self.assertRaisesRegex(RuntimeError, "style:fas,icon:unmapped"):
            self.convert()
        organization.refresh_from_db()
        self.assertEqual(organization.icon, "style:fas,icon:phone")

    def test_migration_alters_both_concrete_fields_before_converting(self):
        self.assertTrue(migration.Migration.atomic)
        self.assertEqual([operation.model_name for operation in migration.Migration.operations[:2]],
                         ["organizationinfostype", "contactinfotype"])
        self.assertFalse(migration.Migration.operations[-1].reversible)
