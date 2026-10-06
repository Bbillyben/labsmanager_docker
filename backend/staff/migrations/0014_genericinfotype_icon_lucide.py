"""Convert Employee icons only; unknown strings remain intact.

Irreversible: the mapping deliberately loses FontAwesome style distinctions.
Restore a pre-migration database backup together with the matching application
version when an exact rollback is required.
"""
from django.db import migrations, models


ICON_MAPPING = {
    "style:fas,icon:id-badge": "Badge",
    "style:far,icon:id-badge": "Badge",
    "style:far,icon:address-book": "Contact",
    "style:fab,icon:searchengin": "Search",
    "style:fas,icon:table-columns": "Columns3",
    "style:fas,icon:user-doctor": "Stethoscope",
}


def convert_icons(apps, schema_editor):
    """Read raw strings using the historical model after AlterField."""
    types = apps.get_model("staff", "GenericInfoType").objects.using(
        schema_editor.connection.alias
    )
    for previous, current in ICON_MAPPING.items():
        types.filter(icon=previous).update(icon=current)


class Migration(migrations.Migration):
    atomic = True
    dependencies = [("staff", "0013_alter_employee_superior_employee")]
    operations = [
        migrations.AlterField(
            model_name="genericinfotype", name="icon",
            field=models.CharField(max_length=50, blank=True, null=True),
        ),
        migrations.RunPython(convert_icons),
    ]
