"""Protect Equipment notes, whose GenericForeignKey has no database FK."""

from django.contrib.contenttypes.models import ContentType
from django.db.models import ProtectedError
from django.db.models.signals import pre_delete
from django.dispatch import receiver

from infos.models import GenericNote

from .models import Equipment


@receiver(pre_delete, sender=Equipment)
def protect_equipment_notes(sender, instance, **kwargs):
    notes = GenericNote.objects.filter(
        content_type=ContentType.objects.get_for_model(Equipment), object_id=instance.pk
    )
    if notes.exists():
        raise ProtectedError("Equipment with notes cannot be deleted.", notes)
