"""Optional credentials that a plugin validates explicitly at its endpoints."""


class TokenMixin:
    """Provide optional technical or user tokens scoped to one plugin.

    ``TOKEN_CONFIG`` declares supported token kinds and scope names. The
    plugin's endpoint must call ``validate_token`` itself; adding this mixin
    does not grant access or expose a token through an API automatically.
    """

    TOKEN_CONFIG = {'plugin': False, 'user': False, 'scopes': {}}

    class MixinMeta:
        MIXIN_NAME = 'TokenMixin'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.add_mixin('token', True, __class__)

    def available_token_scopes(self, kind):
        """Return configured scope choices for the requested token kind."""
        from plugin.tokens import available_scopes
        return available_scopes(self, kind)

    def create_token(self, *, kind, name, user=None, scopes=None, expires_at=None):
        """Create a plugin token and return its one-time plaintext secret.

        Args:
            kind: Configured plugin or user token kind.
            name: Human-readable token label.
            user: Owner for a user token, when applicable.
            scopes: Requested scopes from this plugin's configuration.
            expires_at: Optional expiration datetime.

        Returns:
            A ``(PluginAccessToken, public_id.secret)`` pair. The second value
            is available only at creation time.
        """
        from plugin.tokens import create_token
        return create_token(self, kind=kind, name=name, user=user, scopes=scopes, expires_at=expires_at)

    def validate_token(self, token_value, *, kind=None, required_scopes=None):
        """Validate a secret for this plugin, kind, and required scopes.

        The caller must enforce any additional object-level permissions.
        """
        from plugin.tokens import validate_token
        return validate_token(self, token_value, kind=kind, required_scopes=required_scopes)
