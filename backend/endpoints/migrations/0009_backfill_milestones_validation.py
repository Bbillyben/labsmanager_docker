from datetime import datetime, time

from django.conf import settings
from django.db import migrations, models
from django.utils import timezone


def historical_validation(apps, schema_editor):
    Milestones = apps.get_model("endpoints", "Milestones")
    queryset = Milestones.objects.using(schema_editor.connection.alias)
    # Without an end_date there is no defensible historical validation time.
    queryset.filter(status=True, end_date__isnull=True).update(
        status=False, quotity=0, validated_at=None, validated_by=None,
    )
    for item in queryset.filter(status=True, end_date__isnull=False).only("pk", "end_date").iterator():
        value = datetime.combine(item.end_date, time.min)
        if settings.USE_TZ:
            value = timezone.make_aware(value, timezone.get_default_timezone())
        queryset.filter(pk=item.pk).update(quotity=1, validated_at=value, validated_by=None)
    # Normalize any historical open item saved at 100% by old write paths.
    for item in queryset.filter(status=False, quotity__gte=1).only("pk", "end_date").iterator():
        if item.end_date is None:
            queryset.filter(pk=item.pk).update(quotity=0)
            continue
        value = datetime.combine(item.end_date, time.min)
        if settings.USE_TZ:
            value = timezone.make_aware(value, timezone.get_default_timezone())
        queryset.filter(pk=item.pk).update(status=True, quotity=1, validated_at=value, validated_by=None)


class Migration(migrations.Migration):
    dependencies = [("endpoints", "0008_milestones_validation_fields")]

    operations = [
        migrations.RunPython(historical_validation, migrations.RunPython.noop),
        migrations.AlterModelOptions(
            name="milestones", options={"verbose_name": "Milestone", "verbose_name_plural": "Milestones"},
        ),
        migrations.AddConstraint(
            model_name="milestones",
            constraint=models.CheckConstraint(
                check=(models.Q(status=True, quotity=1, validated_at__isnull=False)
                       | models.Q(status=False, quotity__lt=1, validated_at__isnull=True)),
                name="milestones_completion_validation_coherent",
            ),
        ),
    ]
