"""Session-authenticated management of plugin credentials."""

from datetime import datetime

from django.http import Http404
from django.utils.dateparse import parse_datetime
from rest_framework import permissions, serializers
from rest_framework.response import Response
from rest_framework.views import APIView

from plugin.models import PluginAccessToken
from plugin.registry import registry
from plugin.tokens import TokenError, active_token_config, available_scopes, create_token, revoke_token


def token_data(token):
    return {'public_id': token.public_id, 'name': token.name, 'kind': token.kind,
            'scopes': token.scopes, 'created_at': token.created_at, 'expires_at': token.expires_at,
            'revoked_at': token.revoked_at, 'last_used_at': token.last_used_at}


def token_target(key, kind, user):
    if kind not in PluginAccessToken.Kind.values or (kind == 'plugin' and not user.is_staff):
        raise Http404
    plugin = registry.get_plugin(key)
    if plugin is None:
        raise Http404
    try:
        config = active_token_config(plugin, kind)
    except TokenError:
        raise Http404 from None
    return plugin, config


class TokenCollection(APIView):
    permission_classes = (permissions.IsAuthenticated,)

    def get(self, request, key, kind):
        plugin, config = token_target(key, kind, request.user)
        tokens = PluginAccessToken.objects.filter(plugin=config, kind=kind)
        if kind == 'user':
            tokens = tokens.filter(user=request.user)
        try:
            scopes = available_scopes(plugin, kind)
        except TokenError as error:
            raise serializers.ValidationError({'scopes': str(error)}) from error
        return Response({'scopes': [{'name': name, 'label': str(info.get('label', name)),
                                     'description': str(info.get('description', ''))} for name, info in scopes.items()],
                         'tokens': [token_data(token) for token in tokens.order_by('-created_at', '-pk')]})

    def post(self, request, key, kind):
        plugin, _ = token_target(key, kind, request.user)
        if not isinstance(request.data, dict) or not set(request.data) <= {'name', 'scopes', 'expires_at'}:
            raise serializers.ValidationError({'detail': 'Unexpected token fields.'})
        expires_at = request.data.get('expires_at')
        if expires_at is not None:
            if not isinstance(expires_at, str):
                raise serializers.ValidationError({'expires_at': 'Expected a date-time string.'})
            expires_at = parse_datetime(expires_at)
            if not isinstance(expires_at, datetime):
                raise serializers.ValidationError({'expires_at': 'Invalid date-time.'})
        try:
            token, secret = create_token(plugin, kind=kind, name=request.data.get('name'),
                                         user=request.user if kind == 'user' else None,
                                         scopes=request.data.get('scopes'), expires_at=expires_at)
        except TokenError as error:
            raise serializers.ValidationError({'detail': str(error)}) from error
        return Response({**token_data(token), 'token': secret}, status=201, headers={'Cache-Control': 'no-store'})


class TokenDetail(APIView):
    permission_classes = (permissions.IsAuthenticated,)

    def _token(self, request, key, kind, public_id):
        _, config = token_target(key, kind, request.user)
        tokens = PluginAccessToken.objects.filter(plugin=config, kind=kind, public_id=public_id)
        if kind == 'user':
            tokens = tokens.filter(user=request.user)
        token = tokens.first()
        if token is None:
            raise Http404
        return token

    def patch(self, request, key, kind, public_id):
        token = self._token(request, key, kind, public_id)
        if not isinstance(request.data, dict) or set(request.data) != {'name'}:
            raise serializers.ValidationError({'name': 'Expected one name.'})
        name = request.data['name']
        if not isinstance(name, str) or not name.strip() or len(name.strip()) > 150:
            raise serializers.ValidationError({'name': 'A name of at most 150 characters is required.'})
        token.name = name.strip()
        token.save(update_fields=['name'])
        return Response(token_data(token))

    def delete(self, request, key, kind, public_id):
        token = self._token(request, key, kind, public_id)
        return Response(token_data(revoke_token(token)))
