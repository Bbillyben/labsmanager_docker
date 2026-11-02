"""R2.17 data migration on a real historical GenericNote row."""

from importlib import import_module

from django.contrib.auth import get_user_model
from django.contrib.contenttypes.models import ContentType
from django.db import connection
from django.db.migrations.executor import MigrationExecutor
from django.test import TransactionTestCase

from infos.models import GenericNote
from project.models import Project


class GenericNoteMigrationTests(TransactionTestCase):
    def test_historical_note_receives_explicit_admin_and_object_visibility(self):
        current = [('infos', '0016_genericnote_creator_visibility')]
        executor = MigrationExecutor(connection)
        historical_apps = executor.loader.project_state(current).apps
        migration = import_module('infos.migrations.0016_genericnote_creator_visibility')
        self.assertIs(migration.Migration.operations[-2].code, migration.assign_historical_creator)
        creator_field = GenericNote._meta.get_field('creator')
        nullable_creator = creator_field.clone()
        nullable_creator.set_attributes_from_name(creator_field.name)
        nullable_creator.model = GenericNote
        nullable_creator.remote_field.model = get_user_model()
        nullable_creator.null = True
        # The current test schema is already migrated. Relax only this column
        # to represent a pre-backfill row, without reversing unrelated migrations.
        with connection.schema_editor() as editor:
            editor.alter_field(GenericNote, creator_field, nullable_creator)
        old_note = None
        try:
            admin = get_user_model().objects.create_superuser(username='ben_admin', email='admin@example.test', password='x')
            content_type = ContentType.objects.get_for_model(Project)
            old_note = GenericNote.objects.create(content_type_id=content_type.pk, object_id=123,
                                                  creator=None, visibility='creator', name='Historical', note='<p>Old</p>')
            with connection.schema_editor() as editor:
                migration.assign_historical_creator(historical_apps, editor)
            migrated = GenericNote.objects.get(pk=old_note.pk)
            self.assertEqual(migrated.creator_id, admin.pk)
            self.assertEqual(migrated.visibility, 'object')
            self.assertEqual(migrated.note, '<p>Old</p>')
        finally:
            if old_note is not None:
                GenericNote.objects.filter(pk=old_note.pk).delete()
            with connection.schema_editor() as editor:
                editor.alter_field(GenericNote, nullable_creator, creator_field)
