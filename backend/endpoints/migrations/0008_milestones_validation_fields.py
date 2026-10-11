from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ("endpoints", "0007_alter_milestones_start_date"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AddField(
            model_name="milestones", name="validated_at",
            field=models.DateTimeField(blank=True, null=True, verbose_name="Validated at"),
        ),
        migrations.AddField(
            model_name="milestones", name="validated_by",
            field=models.ForeignKey(
                blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL,
                related_name="+", to=settings.AUTH_USER_MODEL, verbose_name="Validated by",
            ),
        ),
    ]
