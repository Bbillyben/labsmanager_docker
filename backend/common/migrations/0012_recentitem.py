from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ("common", "0011_unique_object_preferences"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="RecentItem",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("url_id", models.CharField(max_length=40)),
                ("obj_id", models.PositiveBigIntegerField(blank=True, null=True)),
                ("last_viewed_at", models.DateTimeField(auto_now=True)),
                ("user", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="recent_items", to=settings.AUTH_USER_MODEL)),
            ],
            options={"ordering": ("-last_viewed_at", "-pk")},
        ),
        migrations.AddConstraint(model_name="recentitem", constraint=models.UniqueConstraint(condition=models.Q(obj_id__isnull=False), fields=("user", "url_id", "obj_id"), name="common_recent_object_unique")),
        migrations.AddConstraint(model_name="recentitem", constraint=models.UniqueConstraint(condition=models.Q(obj_id__isnull=True), fields=("user", "url_id"), name="common_recent_page_unique")),
    ]
