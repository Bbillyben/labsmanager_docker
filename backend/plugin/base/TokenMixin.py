"""Optional credentials that a plugin validates explicitly at its endpoints."""


class TokenMixin:
    TOKEN_CONFIG = {'plugin': False, 'user': False, 'scopes': {}}

    class MixinMeta:
        MIXIN_NAME = 'TokenMixin'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.add_mixin('token', True, __class__)

    def available_token_scopes(self, kind):
        from plugin.tokens import available_scopes
        return available_scopes(self, kind)

    def create_token(self, *, kind, name, user=None, scopes=None, expires_at=None):
        from plugin.tokens import create_token
        return create_token(self, kind=kind, name=name, user=user, scopes=scopes, expires_at=expires_at)

    def validate_token(self, token_value, *, kind=None, required_scopes=None):
        from plugin.tokens import validate_token
        return validate_token(self, token_value, kind=kind, required_scopes=required_scopes)
