"""Shared action capabilities for Data Consistency."""


def can_accept_exception(user):
    """Check permission to accept a consistency exception."""
    return bool(user.is_authenticated and (user.is_staff or
                user.has_perm("data_consistency.add_dataconsistencyexception")))


def can_reopen_exception(user):
    """Check permission to reopen an accepted exception."""
    return bool(user.is_authenticated and (user.is_staff or
                user.has_perm("data_consistency.change_dataconsistencyexception")))


def can_manage_consistency(user):
    """Check administrative access to consistency management."""
    return can_accept_exception(user) or can_reopen_exception(user)
