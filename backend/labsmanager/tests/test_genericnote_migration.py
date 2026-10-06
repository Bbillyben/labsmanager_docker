"""R2.17 data migration on a real historical GenericNote row."""

from django.contrib.auth import get_user_model
from django.contrib.contenttypes.models import ContentType
from django.db import connection
from django.db.migrations.executor import MigrationExecutor
from django.test import TransactionTestCase

from infos.models import GenericNote
from project.models import Project


class GenericNoteMigrationTests(TransactionTestCase):
    def test_historical_note_receives_explicit_admin_and_object_visibility(self):
        previous = [('infos', '0015_alter_contactinfotype_type_and_more')]
        current = [('infos', '0016_genericnote_creator_visibility')]
        executor = MigrationExecutor(connection)
        executor.migrate(previous)
        try:
            old_apps = executor.loader.project_state(previous).apps
            old_note_model = old_apps.get_model('infos', 'GenericNote')
            admin = get_user_model().objects.create_superuser(username='ben_admin', email='admin@example.test', password='x')
            content_type = ContentType.objects.get_for_model(Project)
            old_note = old_note_model.objects.create(content_type_id=content_type.pk, object_id=123, name='Historical', note='<p>Old</p>')
            MigrationExecutor(connection).migrate(current)
            migrated = GenericNote.objects.get(pk=old_note.pk)
            self.assertEqual(migrated.creator_id, admin.pk)
            self.assertEqual(migrated.visibility, 'object')
            self.assertEqual(migrated.note, '<p>Old</p>')
        finally:
            MigrationExecutor(connection).migrate(current)
