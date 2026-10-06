from django.db import migrations


def reset_lab_theme(apps, schema_editor):
    apps.get_model("settings", "LMUserSetting").objects.filter(key__iexact="LAB_THEME").delete()


class Migration(migrations.Migration):
    dependencies = [("settings", "0008_remove_lmprojectsetting_unique_key_and_fund_and_more")]

    operations = [migrations.RunPython(reset_lab_theme, migrations.RunPython.noop)]
