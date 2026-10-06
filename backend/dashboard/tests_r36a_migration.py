"""R3.6a migration preserves a deployed Project Dashboard and its widgets."""

from django.contrib.auth import get_user_model
from django.db import connection
from django.db.migrations.executor import MigrationExecutor
from django.test import TransactionTestCase

from project.models import Project

from .models import Dashboard, WidgetInstance


class GenericDashboardContextMigrationTests(TransactionTestCase):
    def test_project_dashboard_data_is_preserved_and_reverse_restores_project(self):
        before = [("dashboard", "0003_project_dashboard")]
        after = [("dashboard", "0004_generic_dashboard_context")]
        MigrationExecutor(connection).migrate(before)
        try:
            old_apps = MigrationExecutor(connection).loader.project_state(before).apps
            OldDashboard = old_apps.get_model("dashboard", "Dashboard")
            OldWidget = old_apps.get_model("dashboard", "WidgetInstance")
            owner = get_user_model().objects.create_user(username="dashboard-migration-owner")
            project = Project.objects.create(name="Preserved dashboard project")
            old = OldDashboard.objects.create(owner_id=owner.pk, project_id=project.pk,
                                              scope="project", name="Existing", position=0)
            widget = OldWidget.objects.create(dashboard_id=old.pk, definition_key="core.note",
                                              source_key="core.note", renderer_key="empty",
                                              config={"message": "Keep me"}, x=4, y=3, width=4, height=3)
            MigrationExecutor(connection).migrate(after)
            migrated = Dashboard.objects.get(pk=old.pk)
            self.assertEqual(migrated.owner_id, owner.pk)
            self.assertEqual(migrated.context_object, project)
            self.assertEqual(WidgetInstance.objects.get(pk=widget.pk).config, {"message": "Keep me"})
            self.assertEqual(WidgetInstance.objects.get(pk=widget.pk).x, 4)
            MigrationExecutor(connection).migrate(before)
            old_again = MigrationExecutor(connection).loader.project_state(before).apps.get_model("dashboard", "Dashboard")
            self.assertEqual(old_again.objects.get(pk=old.pk).project_id, project.pk)
        finally:
            MigrationExecutor(connection).migrate(after)
