from django import template
from staff.models import Employee

register = template.Library()

@register.simple_tag
def has_lab_perm(perm, user, obj=None):
    if not hasattr(user, "has_perm"):
        return user.has_perm(perm)
    elif user.has_perm(perm, obj):
        return True
    else:
        return user.has_perm(perm)
    
@register.simple_tag
def has_project_add_perm( user):
    if not user.has_perm("project.add_project"):
        return False
    if user.has_perm("project.change_project"):
        return True
    return Employee.objects.filter(user=user).exists()

@register.simple_tag
def has_employee_add_perm( user):
    if not user.has_perm("staff.add_employee"):
        return False
    if user.has_perm("staff.change_employee"):
        return True
    return Employee.objects.filter(user=user).exists()
