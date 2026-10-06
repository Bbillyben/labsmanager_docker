"""Scoped GenericNote API. Parent rights and note visibility are server-side."""

from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ValidationError as ModelValidationError
from django.db import IntegrityError, transaction
from django.db.models import Count, Q
from django.shortcuts import get_object_or_404
from rest_framework import permissions, serializers, status
from rest_framework.exceptions import PermissionDenied
from rest_framework.response import Response
from rest_framework.views import APIView
import nh3

from project.models import Institution, Project
from staff.models import Employee, Team
from expense.models import Contract
from fund.models import Fund_Institution
from labsmanager.admin_links_v1 import get_admin_change_url

from .models import GenericNote


PARENTS = {'project': Project, 'employee': Employee, 'team': Team, 'institution': Institution, 'funder': Fund_Institution, 'contract': Contract}


def parent_for(user, scope, pk):
    model = PARENTS.get(scope)
    if model is None:
        raise serializers.ValidationError({'scope': 'Unsupported note parent.'})
    if model in (Project, Employee):
        queryset = model.get_instances_for_user('view', user, model.objects.filter(pk=pk))
        return get_object_or_404(queryset, pk=pk)
    if model is Contract:
        obj = get_object_or_404(Contract.objects.select_related('fund__project', 'employee'), pk=pk)
        employee_visible = Employee.get_instances_for_user('view', user, Employee.objects.filter(pk=obj.employee_id)).exists()
        if not employee_visible:
            from fund.models import Fund
            from project.models import Participant
            project_visible = Project.get_instances_for_user('view', user, Project.objects.filter(pk=obj.fund.project_id)).exists()
            fund_visible = Fund.get_instances_for_user('view', user, Fund.objects.filter(pk=obj.fund_id)).exists()
            employee_visible = project_visible and fund_visible and Participant.objects.filter(project_id=obj.fund.project_id, employee_id=obj.employee_id).exists()
        if not employee_visible:
            from django.http import Http404
            raise Http404
        return obj
    obj = get_object_or_404(model, pk=pk)
    if model is Team:
        visible = user.has_perm('staff.view_team') or user.has_perm('staff.view_team', obj) or user.has_perm('staff.change_team', obj)
    elif model is Fund_Institution:
        visible = user.has_perm('common.display_infos')
    else:
        visible = user.has_perm('common.display_infos') or user.has_perm('project.view_institution')
    if not visible:
        from django.http import Http404
        raise Http404
    return obj


def note_admin(user):
    return user.is_superuser or user.has_perm('infos.change_genericnote')


def parent_change(user, parent):
    if isinstance(parent, Contract):
        return user.has_perm('expense.change_contract') or user.has_perm('expense.change_contract', parent)
    if isinstance(parent, Employee):
        return user.has_perm('staff.changenote_employee', parent)
    if isinstance(parent, Project):
        return user.has_perm('project.change_project') or user.has_perm('project.change_project', parent)
    if isinstance(parent, Team):
        return user.has_perm('staff.change_team') or user.has_perm('staff.change_team', parent)
    if isinstance(parent, Fund_Institution):
        return user.has_perm('fund.change_fund_institution') or user.has_perm('fund.change_fund_institution', parent)
    return user.has_perm('project.change_institution')


def visible_note_counts(user, model, object_ids):
    """Count only notes visible to this user in one grouped query."""
    ids = list(object_ids)
    if not ids:
        return {}
    notes = GenericNote.objects.filter(content_type=ContentType.objects.get_for_model(model), object_id__in=ids)
    if not note_admin(user):
        notes = notes.filter(Q(visibility='object') | Q(visibility='creator', creator=user))
    return dict(notes.values_list('object_id').annotate(total=Count('pk')))


def capabilities(user, parent, note=None):
    administer = note_admin(user)
    can_write = administer or parent_change(user, parent)
    can_see = note is None or note.visibility == 'object' or administer or note.creator_id == user.pk
    return {
        'can_add': can_write,
        'can_change': bool(can_see and can_write),
        'can_rename': bool(can_see and can_write),
        'can_delete': bool(can_see and can_write),
        'can_change_visibility': bool(note and can_see and (administer or note.creator_id == user.pk)),
    }


def serialize_note(note, user, parent):
    creator = note.creator
    return {
        'id': note.pk, 'admin_url': get_admin_change_url(user, note), 'name': note.name, 'note': nh3.clean(note.note or ''),
        'visibility': note.visibility,
        'creator': {'id': creator.pk, 'name': creator.get_full_name() or creator.get_username()},
        'created_at': note.created_at, 'updated_at': note.updated_at,
        'capabilities': capabilities(user, parent, note),
    }


def legacy_visible_notes(user, action='view'):
    """Keep old note URLs from bypassing the new visibility contract."""
    from django.http import Http404
    allowed = []
    scopes = {model: scope for scope, model in PARENTS.items()}
    for note in GenericNote.objects.select_related('content_type', 'creator').all():
        scope = scopes.get(note.content_type.model_class())
        if scope is None:
            continue
        try:
            parent = parent_for(user, scope, note.object_id)
        except Http404:
            continue
        if note.visibility == 'creator' and not (note_admin(user) or note.creator_id == user.pk):
            continue
        if action == 'change' and not capabilities(user, parent, note)['can_change']:
            continue
        if action == 'delete' and not capabilities(user, parent, note)['can_delete']:
            continue
        allowed.append(note.pk)
    return GenericNote.objects.filter(pk__in=allowed)


def validate_and_save(note):
    if GenericNote.objects.filter(content_type=note.content_type, object_id=note.object_id, name=note.name).exclude(pk=note.pk).exists():
        raise serializers.ValidationError({'name': ['already_exists']})
    try:
        note.full_clean()
        note.save()
    except ModelValidationError as error:
        raise serializers.ValidationError(getattr(error, 'message_dict', None) or error.messages) from error
    except IntegrityError as error:
        raise serializers.ValidationError({'name': ['already_exists']}) from error


class NoteContext:
    def resolve(self, request, scope, pk):
        parent = parent_for(request.user, scope, pk)
        content_type = ContentType.objects.get_for_model(parent)
        return parent, content_type

    def note(self, request, parent, content_type, pk, note_id):
        note = get_object_or_404(
            GenericNote.objects.select_related('creator'), content_type=content_type,
            object_id=pk, pk=note_id,
        )
        if note.visibility == 'creator' and not (note_admin(request.user) or note.creator_id == request.user.pk):
            from django.http import Http404
            raise Http404
        return note


class GenericNotesCollectionV1View(NoteContext, APIView):
    permission_classes = (permissions.IsAuthenticated,)

    def get(self, request, scope, pk):
        parent, content_type = self.resolve(request, scope, pk)
        notes = GenericNote.objects.filter(content_type=content_type, object_id=pk).select_related('creator')
        if not note_admin(request.user):
            notes = notes.filter(visibility='object') | notes.filter(visibility='creator', creator=request.user)
        return Response({
            'capabilities': {'can_add': capabilities(request.user, parent)['can_add']},
            'items': [serialize_note(note, request.user, parent) for note in notes],
        })

    @transaction.atomic
    def post(self, request, scope, pk):
        parent, content_type = self.resolve(request, scope, pk)
        if not capabilities(request.user, parent)['can_add']:
            raise PermissionDenied()
        allowed = {'name', 'visibility'}
        if set(request.data) - allowed:
            raise serializers.ValidationError({'detail': 'Unsupported note fields.'})
        name = request.data.get('name')
        visibility = request.data.get('visibility', 'object')
        if not isinstance(name, str) or not name.strip():
            raise serializers.ValidationError({'name': 'This field is required.'})
        if visibility not in ('object', 'creator'):
            raise serializers.ValidationError({'visibility': 'Invalid visibility.'})
        note = GenericNote(content_type=content_type, object_id=pk, name=name.strip(), note='', visibility=visibility, creator=request.user)
        validate_and_save(note)
        return Response(serialize_note(note, request.user, parent), status=status.HTTP_201_CREATED)


class GenericNoteDetailV1View(NoteContext, APIView):
    permission_classes = (permissions.IsAuthenticated,)

    def get(self, request, scope, pk, note_id):
        parent, content_type = self.resolve(request, scope, pk)
        return Response(serialize_note(self.note(request, parent, content_type, pk, note_id), request.user, parent))

    @transaction.atomic
    def patch(self, request, scope, pk, note_id):
        parent, content_type = self.resolve(request, scope, pk)
        note = self.note(request, parent, content_type, pk, note_id)
        fields = set(request.data)
        if not fields or fields - {'note', 'name', 'visibility'}:
            raise serializers.ValidationError({'detail': 'Unsupported note fields.'})
        rights = capabilities(request.user, parent, note)
        if ('note' in fields or 'name' in fields) and not rights['can_change']:
            raise PermissionDenied()
        if 'visibility' in fields and not rights['can_change_visibility']:
            raise PermissionDenied()
        if 'name' in fields:
            value = request.data['name']
            if not isinstance(value, str) or not value.strip():
                raise serializers.ValidationError({'name': 'This field is required.'})
            note.name = value.strip()
        if 'note' in fields:
            if not isinstance(request.data['note'], str):
                raise serializers.ValidationError({'note': 'Expected HTML text.'})
            note.note = request.data['note']
        if 'visibility' in fields:
            if request.data['visibility'] not in ('object', 'creator'):
                raise serializers.ValidationError({'visibility': 'Invalid visibility.'})
            note.visibility = request.data['visibility']
        validate_and_save(note)
        return Response(serialize_note(note, request.user, parent))

    @transaction.atomic
    def delete(self, request, scope, pk, note_id):
        parent, content_type = self.resolve(request, scope, pk)
        note = self.note(request, parent, content_type, pk, note_id)
        if not capabilities(request.user, parent, note)['can_delete']:
            raise PermissionDenied()
        note.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
