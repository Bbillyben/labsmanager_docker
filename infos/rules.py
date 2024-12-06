import rules
from django.apps import apps
from django.shortcuts import render, get_object_or_404

#    Predicates ======================

@rules.predicate
def is_user_custom_note(user, rulesname):
    print(f" >>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>   is_user_custom_note : {user} / {rulesname}")
    perms=rulesname.split("#")
    perm_name = rulesname[0]
    pk=rulesname[1]
    # print(f"[PreciCate is_user_custom_note] : {user} / {perm_name} - {pk}")
    if not rules.perm_exists(perm_name):
        return False
    app_def=perm_name.split(".change_")
    model_class = apps.get_model(app_label=app_def[0], model_name=app_def[1])
    obj = get_object_or_404(model_class, pk=pk)
    if not obj:
        return False
    return user.has_perm(perm_name, obj)

from staff.rules import is_user_subordinate
@rules.predicate
def is_user_employee_note(user, employee):
    print(f">>>>>>>>>>>>  is_user_employee_note : {user} = {employee} ({employee.user})")
    if not employee:
        return False
    return (employee.user == user)

#    Rules ======================
rules.add_perm('custom_perm_note', is_user_custom_note)
rules.add_perm('staff.changenote_employee', is_user_employee_note | is_user_subordinate)