"""Protect existing Equipment rows when categories acquire MPTT fields."""

from django.db import connection
from django.db.migrations.executor import MigrationExecutor
from django.test import TransactionTestCase


class EquipmentCategoryTreeMigrationTests(TransactionTestCase):
    def test_existing_categories_become_roots_without_replacing_equipment(self):
        if connection.vendor != "postgresql":
            self.skipTest("Migration preservation is checked on PostgreSQL.")
        executor = MigrationExecutor(connection)
        previous = [("equipment", "0003_equipmentmaintenance")]
        current = [("equipment", "0004_equipmentcategory_tree")]
        executor.migrate(previous)
        old_apps = executor.loader.project_state(previous).apps
        category_model = old_apps.get_model("equipment", "EquipmentCategory")
        equipment_model = old_apps.get_model("equipment", "Equipment")
        category = category_model.objects.create(name="Existing", is_active=False)
        second = category_model.objects.create(name="Second")
        equipment = equipment_model.objects.create(
            name="Existing equipment", internal_reference="EQ-MIGRATION", category_id=category.pk,
            status="retired",
        )
        executor = MigrationExecutor(connection)
        executor.migrate(current)
        new_apps = executor.loader.project_state(current).apps
        migrated = new_apps.get_model("equipment", "EquipmentCategory").objects.get(pk=category.pk)
        second_migrated = new_apps.get_model("equipment", "EquipmentCategory").objects.get(pk=second.pk)
        linked = new_apps.get_model("equipment", "Equipment").objects.get(pk=equipment.pk)
        self.assertEqual((migrated.parent_id, migrated.level, migrated.lft, migrated.rght), (None, 0, 1, 2))
        self.assertGreater(migrated.tree_id, 0)
        self.assertNotEqual(migrated.tree_id, second_migrated.tree_id)
        self.assertEqual((second_migrated.parent_id, second_migrated.level, second_migrated.lft,
                          second_migrated.rght), (None, 0, 1, 2))
        self.assertEqual((migrated.name, migrated.is_active), ("Existing", False))
        self.assertEqual((linked.category_id, linked.internal_reference, linked.status),
                         (category.pk, "EQ-MIGRATION", "retired"))
