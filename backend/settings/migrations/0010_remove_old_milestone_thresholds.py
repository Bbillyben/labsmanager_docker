from django.db import migrations
from django.db.models import Q


def remove_old_milestone_thresholds(apps, schema_editor):
    apps.get_model("settings", "LMUserSetting").objects.filter(
        Q(key__iexact="NOTIFICATION_ENDPOINTS_MILESTONES_STALE")
        | Q(key__iexact="DASHBOARD_MILESTONES_STALE_TO_MONTH")
    ).delete()


class Migration(migrations.Migration):
    dependencies = [("settings", "0009_reset_lab_theme")]

    operations = [migrations.RunPython(remove_old_milestone_thresholds, migrations.RunPython.noop)]
