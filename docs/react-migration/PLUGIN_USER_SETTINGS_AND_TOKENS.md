# Plugin user settings and tokens

Plugin features for authors and users. Apply plugin migrations `0002` and `0003` before use.

## Personal settings

`SettingsMixin` keeps global `SETTINGS` unchanged and accepts `USER_SETTINGS` with the same definitions (`name`, `description`, `default`, `validator`, `choices`, etc.). Values are stored in `UserPluginSetting` by `(plugin, user, key)`; reading a default creates no database row.

```python
class ExamplePlugin(SettingsMixin, LabManagerPlugin):
    USER_SETTINGS = {
        'DISPLAY_MODE': {'name': 'Display mode', 'description': 'Personal view',
                         'default': 'compact', 'choices': [('compact', 'Compact'), ('wide', 'Wide')]},
    }

    def example(self, user):
        mode = self.get_user_setting('DISPLAY_MODE', user)
        self.set_user_setting('DISPLAY_MODE', 'wide', user)
        self.reset_user_setting('DISPLAY_MODE', user)
```

The current-user API is `GET /api/v1/plugins/<slug>/user-settings/`, `PATCH` or `DELETE /api/v1/plugins/<slug>/user-settings/<key>/`. `PATCH` accepts only `{"value": ...}`. Authentication and the ordinary session CSRF rules apply. Inactive plugin definitions disappear from the API; saved values remain.

React lists active plugins with personal settings or personal tokens under **Settings > My plugins** (`/app/settings/my-plugins`). `GET /api/v1/plugins/mine/` supplies their names, descriptions and capabilities; it does not expose stored setting values. Each plugin has a detail page at `/app/settings/my-plugins/<slug>`. Settings use their declared definitions and can be saved or reset to the default. Plugins with no personal capabilities are omitted.

## Tokens

`TokenMixin` is imported from `plugin.mixins`. Both kinds are disabled by default. A technical `PluginToken` has no user; a personal `UserPluginToken` belongs to one user. Both are rows in `PluginAccessToken`, and multiple rows per plugin or user are allowed.

```python
class PlainPlugin(TokenMixin, LabManagerPlugin):
    TOKEN_CONFIG = {'plugin': True, 'user': True}

    def check(self, raw_token):
        context = self.validate_token(raw_token, kind='user')
        return context.user
```

Scopes are optional. When declared, each scope states which kinds may receive it:

```python
TOKEN_CONFIG = {
    'plugin': True, 'user': True,
    'scopes': {
        'read': {'label': 'Read', 'description': 'Read data', 'plugin': True, 'user': True},
        'write': {'label': 'Write', 'description': 'Change data', 'plugin': True, 'user': False},
    },
}

context = self.validate_token(raw_token, kind='user', required_scopes=['read'])
```

`self.available_token_scopes(kind)` lists allowed scopes. `self.create_token(kind=..., name=..., user=..., scopes=..., expires_at=...)` returns `(record, raw_token)`. The raw token is `<public_id>.<secret>` and is shown only at creation. Validation returns a `TokenContext` with `plugin`, `kind`, `user`, `scopes`, and `public_id`; failures raise `TokenError`. A plugin with no declared scopes accepts an empty selection but rejects `required_scopes` during validation.

The user endpoints are `GET/POST /api/v1/plugins/<slug>/tokens/user/` and `PATCH/DELETE /api/v1/plugins/<slug>/tokens/user/<public_id>/`. The technical equivalents use `plugin` in place of `user` and require staff permission. `GET` returns available scopes and token metadata; `POST` returns the raw token once. `PATCH` changes only the name; `DELETE` records revocation. Django Admin has **Plugin tokens** for technical token creation, listing and revocation. Creation shows a one-time copy field.

The React plugin detail in Admin shows technical tokens when `TOKEN_CONFIG.plugin` is enabled; the personal plugin detail in Settings shows personal tokens when `TOKEN_CONFIG.user` is enabled. Both use the same token manager for multiple tokens, optional expiration and declared scopes, renaming, confirmed revocation and a one-time secret reveal. The secret is removed from the manager when its reveal panel closes. Copy uses the Clipboard API where available and falls back to selecting and copying the field on HTTP network hosts; the field stays selectable for manual copying. The server remains authoritative for permission and capability checks.

Secrets are generated independently from public identifiers, stored only as password hashes, and never returned by list/detail endpoints. Ownership comes from the database or `request.user`, never a submitted user ID. Scopes and identity cannot be changed after creation. Validation checks the current active plugin, token kind, hash, expiry, revocation, allowed scopes and active user. Plugins must call `validate_token()` explicitly; this mixin does not authenticate DRF requests or grant endpoint permissions.
