"""Creation and explicit validation of plugin-owned credentials."""

import secrets
from dataclasses import dataclass

from django.contrib.auth.hashers import check_password, make_password
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.utils import timezone

from plugin.models import PluginAccessToken
from plugin.registry import registry


class TokenError(ValueError):
    """A token cannot be created or validated (safe to show without the secret)."""


@dataclass(frozen=True)
class TokenContext:
    plugin: object
    kind: str
    user: object
    scopes: tuple[str, ...]
    public_id: str


def active_token_config(plugin, kind):
    if kind not in PluginAccessToken.Kind.values:
        raise TokenError('Unknown token kind.')
    if registry.get_plugin(plugin.slug) is not plugin or not plugin.mixin_enabled('token'):
        raise TokenError('Plugin is inactive or does not provide tokens.')
    config = registry.get_plugin_config(plugin.slug)
    if config is None or not config.active:
        raise TokenError('Plugin is inactive.')
    token_config = getattr(plugin, 'TOKEN_CONFIG', {})
    if token_config.get(kind) is not True:
        raise TokenError('Token kind is not enabled for this plugin.')
    return config


def available_scopes(plugin, kind):
    active_token_config(plugin, kind)
    declared = getattr(plugin, 'TOKEN_CONFIG', {}).get('scopes') or {}
    if not isinstance(declared, dict):
        raise TokenError('Invalid token scope declaration.')
    return {name: info for name, info in declared.items()
            if isinstance(name, str) and isinstance(info, dict) and info.get(kind) is True}


def validate_scopes(plugin, kind, scopes):
    if not isinstance(scopes, list) or any(not isinstance(scope, str) for scope in scopes) or len(set(scopes)) != len(scopes):
        raise TokenError('Scopes must be a list of distinct names.')
    allowed = available_scopes(plugin, kind)
    if any(scope not in allowed for scope in scopes):
        raise TokenError('Unknown or forbidden scope.')
    return scopes


def create_token(plugin, *, kind, name, user=None, scopes=None, expires_at=None):
    config = active_token_config(plugin, kind)
    if (kind == PluginAccessToken.Kind.USER) != (user is not None):
        raise TokenError('Token owner does not match kind.')
    if user is not None and not user.is_active:
        raise TokenError('Token owner is inactive.')
    if not isinstance(name, str) or not name.strip() or len(name.strip()) > 150:
        raise TokenError('A token name of at most 150 characters is required.')
    if expires_at is not None and (timezone.is_naive(expires_at) or expires_at <= timezone.now()):
        raise TokenError('Expiration must be in the future.')
    scopes = validate_scopes(plugin, kind, scopes if scopes is not None else [])
    # Each retry has a fresh public identifier; the private secret is independent.
    for _ in range(5):
        public_id = secrets.token_urlsafe(18)
        secret = secrets.token_urlsafe(32)
        try:
            with transaction.atomic():
                token = PluginAccessToken.objects.create(
                    plugin=config, kind=kind, user=user, name=name.strip(), public_id=public_id,
                    secret_hash=make_password(secret), scopes=scopes, expires_at=expires_at,
                )
            return token, f'{public_id}.{secret}'
        except (IntegrityError, ValidationError):
            if PluginAccessToken.objects.filter(public_id=public_id).exists():
                continue
            raise
    raise TokenError('Could not allocate a unique token identifier.')


def validate_token(plugin, token_value, *, kind=None, required_scopes=None):
    if kind is not None:
        active_token_config(plugin, kind)
    else:
        # Check active state before even looking up the credential.
        if registry.get_plugin(plugin.slug) is not plugin or not plugin.mixin_enabled('token'):
            raise TokenError('Plugin is inactive or does not provide tokens.')
    if not isinstance(token_value, str) or token_value.count('.') != 1:
        raise TokenError('Invalid token.')
    public_id, secret = token_value.split('.', 1)
    if not public_id or not secret:
        raise TokenError('Invalid token.')
    token = PluginAccessToken.objects.select_related('user').filter(public_id=public_id, plugin__key=plugin.slug).first()
    if token is None or not check_password(secret, token.secret_hash):
        raise TokenError('Invalid token.')
    active_token_config(plugin, token.kind)
    if kind is not None and token.kind != kind:
        raise TokenError('Wrong token kind.')
    now = timezone.now()
    if token.revoked_at is not None:
        raise TokenError('Token is revoked.')
    if token.expires_at is not None and token.expires_at <= now:
        raise TokenError('Token is expired.')
    if token.kind == PluginAccessToken.Kind.USER and (token.user is None or not token.user.is_active):
        raise TokenError('Token owner is inactive.')
    if token.kind == PluginAccessToken.Kind.PLUGIN and token.user_id is not None:
        raise TokenError('Invalid token owner.')
    required_scopes = required_scopes or []
    if not isinstance(required_scopes, (list, tuple)) or any(not isinstance(scope, str) for scope in required_scopes):
        raise TokenError('Invalid required scopes.')
    if required_scopes:
        allowed = available_scopes(plugin, token.kind)
        if not allowed or any(scope not in allowed or scope not in token.scopes for scope in required_scopes):
            raise TokenError('Required scope is missing.')
    PluginAccessToken.objects.filter(pk=token.pk).update(last_used_at=now)
    return TokenContext(plugin=plugin, kind=token.kind, user=token.user, scopes=tuple(token.scopes), public_id=token.public_id)


def revoke_token(token):
    if token.revoked_at is None:
        token.revoked_at = timezone.now()
        token.save(update_fields=['revoked_at'])
    return token
