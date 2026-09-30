from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


def assign_historical_creator(apps, schema_editor):
    Note = apps.get_model("infos", "GenericNote")
    User = apps.get_model(*settings.AUTH_USER_MODEL.split("."))
    database = schema_editor.connection.alias

    notes = Note.objects.using(database).filter(creator__isnull=True)

    if not notes.exists():
        return

    admin = (
        User.objects.using(database)
        .filter(is_superuser=True, is_active=True)
        .order_by("pk")
        .first()
    )

    if admin is None:
        raise RuntimeError(
            "R2.17 requires at least one active superuser "
            "to assign historical GenericNote creators."
        )

    for note in notes.iterator():
        note.creator_id = admin.pk
        note.visibility = "object"
        note.save(using=database)


class Migration(migrations.Migration):
    dependencies = [
        ('infos', '0015_alter_contactinfotype_type_and_more'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AddField(
            model_name='genericnote', name='creator',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.PROTECT, related_name='generic_notes', to=settings.AUTH_USER_MODEL),
        ),
        migrations.AddField(
            model_name='genericnote', name='visibility',
            field=models.CharField(choices=[('object', 'Object viewers'), ('creator', 'Creator only')], default='object', max_length=7),
        ),
        migrations.RunPython(assign_historical_creator, migrations.RunPython.noop),
        migrations.AlterField(
            model_name='genericnote', name='creator',
            field=models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='generic_notes', to=settings.AUTH_USER_MODEL),
        ),
    ]
