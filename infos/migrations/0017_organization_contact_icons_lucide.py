"""Convert Organization and Contact information icons to Lucide identifiers.

Unknown nonempty values abort the migration; NULL and empty strings are kept.
The conversion is irreversible because Font Awesome style data is lost.
"""

from django.db import migrations, models


ICON_MAPPING = {
    "style:fas,icon:signs-post": "Signpost",
    "style:fab,icon:adn": "Dna",
    "style:fas,icon:piggy-bank": "PiggyBank",
    "style:fas,icon:address-book": "BookUser",
    "style:fas,icon:flag": "Flag",
    "style:fas,icon:fax": "Printer",
    "style:fas,icon:building-columns": "Landmark",
    "style:fas,icon:sack-dollar": "BadgeDollarSign",
    "style:far,icon:id-card": "IdCard",
    "style:fas,icon:building-flag": "Building2",
    "style:fas,icon:phone": "Phone",
    "style:fas,icon:link": "Link",
    "style:fas,icon:location-dot": "MapPin",
    "style:fas,icon:envelope": "Mail",
}


def convert_icons(apps, schema_editor):
    database = schema_editor.connection.alias
    models_to_convert = [
        apps.get_model("infos", "OrganizationInfosType"),
        apps.get_model("infos", "ContactInfoType"),
    ]
    known = [*ICON_MAPPING, *ICON_MAPPING.values()]

    # Validate both tables before writing either one.
    for model in models_to_convert:
        unknown = list(
            model.objects.using(database).exclude(icon__isnull=True).exclude(icon="")
            .exclude(icon__in=known).order_by("icon").values_list("icon", flat=True).distinct()
        )
        if unknown:
            raise RuntimeError(f"Unknown {model.__name__} icon values: {unknown}")

    for model in models_to_convert:
        types = model.objects.using(database)
        for previous, current in ICON_MAPPING.items():
            types.filter(icon=previous).update(icon=current)


class Migration(migrations.Migration):
    atomic = True
    dependencies = [("infos", "0016_genericnote_creator_visibility")]
    operations = [
        migrations.AlterField(
            model_name="organizationinfostype", name="icon",
            field=models.CharField(max_length=50, blank=True, null=True),
        ),
        migrations.AlterField(
            model_name="contactinfotype", name="icon",
            field=models.CharField(max_length=50, blank=True, null=True),
        ),
        migrations.RunPython(convert_icons),
    ]
