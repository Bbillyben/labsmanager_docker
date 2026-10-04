"""Move already deployed Project Dashboard links to generic context storage."""

from django.db import migrations, models
from django.db.models import F, Q
import django.db.models.deletion


def project_to_context(apps, schema_editor):
    Dashboard = apps.get_model("dashboard", "Dashboard")
    ContentType = apps.get_model("contenttypes", "ContentType")
    project_type, _created = ContentType.objects.using(schema_editor.connection.alias).get_or_create(
        app_label="project", model="project",
    )
    Dashboard.objects.using(schema_editor.connection.alias).filter(project_id__isnull=False).update(
        context_content_type_id=project_type.pk, context_object_id=F("project_id"),
    )


def context_to_project(apps, schema_editor):
    Dashboard = apps.get_model("dashboard", "Dashboard")
    ContentType = apps.get_model("contenttypes", "ContentType")
    alias = schema_editor.connection.alias
    project_type = ContentType.objects.using(alias).filter(app_label="project", model="project").first()
    other_contexts = Dashboard.objects.using(alias).filter(context_content_type_id__isnull=False)
    if project_type:
        other_contexts = other_contexts.exclude(context_content_type_id=project_type.pk)
    if other_contexts.exists():
        raise RuntimeError("Cannot reverse Dashboard context migration with non-Project contexts.")
    if project_type:
        Dashboard.objects.using(alias).filter(context_content_type_id=project_type.pk).update(
            project_id=F("context_object_id"),
        )


class Migration(migrations.Migration):
    dependencies = [
        ("dashboard", "0003_project_dashboard"),
        ("contenttypes", "0002_remove_content_type_name"),
    ]

    operations = [
        migrations.RemoveConstraint(model_name="dashboard", name="dashboard_one_per_project_owner"),
        migrations.AddField(
            model_name="dashboard", name="context_content_type",
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE,
                                    related_name="context_dashboards", to="contenttypes.contenttype"),
        ),
        migrations.AddField(
            model_name="dashboard", name="context_object_id",
            field=models.PositiveBigIntegerField(blank=True, null=True),
        ),
        migrations.RunPython(project_to_context, context_to_project),
        migrations.AddConstraint(
            model_name="dashboard",
            constraint=models.UniqueConstraint(
                fields=("owner", "context_content_type", "context_object_id"),
                condition=Q(context_content_type__isnull=False), name="dashboard_one_per_owner_context",
            ),
        ),
        migrations.AddConstraint(
            model_name="dashboard",
            constraint=models.CheckConstraint(
                check=Q(context_content_type__isnull=True, context_object_id__isnull=True)
                | Q(context_content_type__isnull=False, context_object_id__isnull=False),
                name="dashboard_context_fields_together",
            ),
        ),
        migrations.AddIndex(
            model_name="dashboard",
            index=models.Index(fields=("context_content_type", "context_object_id"), name="dashboard_context_idx"),
        ),
        migrations.RemoveField(model_name="dashboard", name="project"),
    ]
