from django.db import migrations, models
from django.db.models import Count


def remove_duplicate_preferences(apps, schema_editor):
    # Keep the oldest relation (lowest primary key) for each user/object.
    for name in ("favorite", "subscription"):
        model = apps.get_model("common", name)
        duplicates = model.objects.using(schema_editor.connection.alias).values(
            "user_id", "content_type_id", "object_id"
        ).annotate(total=Count("pk")).filter(total__gt=1)
        for key in duplicates.iterator():
            ids = list(model.objects.using(schema_editor.connection.alias).filter(
                user_id=key["user_id"], content_type_id=key["content_type_id"],
                object_id=key["object_id"],
            ).order_by("pk").values_list("pk", flat=True))
            for instance in model.objects.using(schema_editor.connection.alias).filter(pk__in=ids[1:]):
                instance.delete()


class Migration(migrations.Migration):
    dependencies = [("common", "0010_alter_rightssupport_options")]

    operations = [
        migrations.RunPython(remove_duplicate_preferences, migrations.RunPython.noop),
        migrations.AddConstraint(model_name="favorite", constraint=models.UniqueConstraint(fields=("user", "content_type", "object_id"), name="common_favorite_user_object_unique")),
        migrations.AddConstraint(model_name="subscription", constraint=models.UniqueConstraint(fields=("user", "content_type", "object_id"), name="common_subscription_user_object_unique")),
    ]
