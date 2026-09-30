"""Convert Project information icons to Lucide identifiers.

Unknown strings, empty strings, and NULL remain unchanged, matching staff.0014.
The conversion is irreversible because Font Awesome style information is lost.
"""
from django.db import migrations, models


ICON_MAPPING = {
    "style:fas,icon:building-columns": "Landmark",
    "style:fas,icon:book": "BookOpen",
    "style:fas,icon:bookmark": "Bookmark",
    "style:fab,icon:cloudversify": "Cloud",
    "style:fas,icon:user-tie": "UserRoundCheck",
}


def convert_icons(apps, schema_editor):
    types = apps.get_model("project", "GenericInfoTypeProject").objects.using(
        schema_editor.connection.alias
    )
    for previous, current in ICON_MAPPING.items():
        types.filter(icon=previous).update(icon=current)


class Migration(migrations.Migration):
    atomic = True
    dependencies = [("project", "0007_remove_institution_adress")]
    operations = [
        migrations.AlterField(
            model_name="genericinfotypeproject", name="icon",
            field=models.CharField(max_length=50, blank=True, null=True),
        ),
        migrations.RunPython(convert_icons),
    ]
