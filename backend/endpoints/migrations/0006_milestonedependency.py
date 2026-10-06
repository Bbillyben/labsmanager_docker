from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ("endpoints", "0005_milestones_start_date"),
    ]

    operations = [
        migrations.CreateModel(
            name="MilestoneDependency",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("predecessor", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="outgoing_dependencies", to="endpoints.milestones")),
                ("successor", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="incoming_dependencies", to="endpoints.milestones")),
            ],
        ),
        migrations.AddConstraint(
            model_name="milestonedependency",
            constraint=models.CheckConstraint(check=~models.Q(predecessor=models.F("successor")), name="milestone_dependency_no_self"),
        ),
        migrations.AddConstraint(
            model_name="milestonedependency",
            constraint=models.UniqueConstraint(fields=("predecessor", "successor"), name="milestone_dependency_unique_pair"),
        ),
    ]
