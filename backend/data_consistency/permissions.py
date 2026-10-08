"""Shared action capabilities for Data Consistency."""


def can_accept_exception(user):
    return bool(user.is_authenticated and (user.is_staff or
                user.has_perm("data_consistency.add_dataconsistencyexception")))


def can_reopen_exception(user):
    return bool(user.is_authenticated and (user.is_staff or
                user.has_perm("data_consistency.change_dataconsistencyexception")))


def can_manage_consistency(user):
    return can_accept_exception(user) or can_reopen_exception(user)
