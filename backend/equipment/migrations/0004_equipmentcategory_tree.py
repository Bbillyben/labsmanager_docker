"""Initialize existing equipment categories as MPTT roots without replacing rows."""

from django.db import migrations, models
import django.db.models.deletion
import mptt.fields


def initialize_roots(apps, schema_editor):
    category = apps.get_model("equipment", "EquipmentCategory")
    database = schema_editor.connection.alias
    ids = category.objects.using(database).order_by("name", "pk").values_list("pk", flat=True)
    for tree_id, pk in enumerate(ids, start=1):
        category.objects.using(database).filter(pk=pk).update(
            tree_id=tree_id, lft=1, rght=2, level=0
        )


class Migration(migrations.Migration):
    dependencies = [("equipment", "0003_equipmentmaintenance")]

    operations = [
        migrations.AddField(
            model_name="equipmentcategory", name="parent",
            field=mptt.fields.TreeForeignKey(
                to="equipment.equipmentcategory", on_delete=django.db.models.deletion.PROTECT,
                null=True, blank=True, related_name="children", verbose_name="Parent",
            ),
        ),
        migrations.AddField(model_name="equipmentcategory", name="lft",
                            field=models.PositiveIntegerField(null=True, editable=False)),
        migrations.AddField(model_name="equipmentcategory", name="rght",
                            field=models.PositiveIntegerField(null=True, editable=False)),
        migrations.AddField(model_name="equipmentcategory", name="tree_id",
                            field=models.PositiveIntegerField(null=True, db_index=True, editable=False)),
        migrations.AddField(model_name="equipmentcategory", name="level",
                            field=models.PositiveIntegerField(null=True, editable=False)),
        migrations.RunPython(initialize_roots, migrations.RunPython.noop),
        migrations.AlterField(model_name="equipmentcategory", name="lft",
                              field=models.PositiveIntegerField(editable=False)),
        migrations.AlterField(model_name="equipmentcategory", name="rght",
                              field=models.PositiveIntegerField(editable=False)),
        migrations.AlterField(model_name="equipmentcategory", name="tree_id",
                              field=models.PositiveIntegerField(db_index=True, editable=False)),
        migrations.AlterField(model_name="equipmentcategory", name="level",
                              field=models.PositiveIntegerField(editable=False)),
        migrations.AlterModelOptions(
            name="equipmentcategory",
            options={"ordering": ("tree_id", "lft"), "verbose_name": "Equipment category",
                     "verbose_name_plural": "Equipment categories"},
        ),
    ]
