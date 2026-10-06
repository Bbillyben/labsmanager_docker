from django.db import migrations, models


def populate_source(apps, schema_editor):
    Widget = apps.get_model('dashboard', 'WidgetInstance')
    keys = {'core.quick-links': 'core.links', 'core.note': 'core.note',
            'core.projects-count': 'core.projects'}
    for definition_key, source_key in keys.items():
        Widget.objects.filter(definition_key=definition_key).update(source_key=source_key)


class Migration(migrations.Migration):
    dependencies = [('dashboard', '0001_initial')]
    operations = [
        migrations.AddField(model_name='widgetinstance', name='source_key',
                            field=models.CharField(blank=True, max_length=160)),
        migrations.RunPython(populate_source, migrations.RunPython.noop),
    ]
