from django.db import migrations, models
from django.db.models import Q
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ("dashboard", "0002_widget_source"),
        ("project", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="dashboard", name="project",
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE,
                                    related_name="dashboards", to="project.project"),
        ),
        migrations.AddConstraint(
            model_name="dashboard",
            constraint=models.UniqueConstraint(fields=("owner", "project"), condition=Q(scope="project"),
                                               name="dashboard_one_per_project_owner"),
        ),
    ]
