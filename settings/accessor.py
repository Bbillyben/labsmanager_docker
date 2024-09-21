"""User-configurable settings for the common app."""

from os import environ


def get_global_setting(key, backup_value=None, enviroment_key=None, **kwargs):
    """Return the value of a global setting using the provided key."""
    from settings.models import LabsManagerSetting

    if enviroment_key:
        value = environ.get(enviroment_key)
        if value:
            return value

    if backup_value is not None:
        kwargs['backup_value'] = backup_value

    return LabsManagerSetting.get_setting(key, **kwargs)


def set_global_setting(key, value, change_user=None, create=True, **kwargs):
    """Set the value of a global setting using the provided key."""
    from settings.models import LabsManagerSetting

    kwargs['change_user'] = change_user
    kwargs['create'] = create

    return LabsManagerSetting.set_setting(key, value, **kwargs)


def get_user_setting(key, user, backup_value=None, **kwargs):
    """Return the value of a user-specific setting using the provided key."""
    from settings.models import LMUserSetting

    kwargs['user'] = user

    if backup_value is not None:
        kwargs['backup_value'] = backup_value

    return LMUserSetting.get_setting(key, **kwargs)


def set_user_setting(key, value, user, **kwargs):
    """Set the value of a user-specific setting using the provided key."""
    from settings.models import LMUserSetting

    kwargs['user'] = user

    return LMUserSetting.set_setting(key, value, **kwargs)

