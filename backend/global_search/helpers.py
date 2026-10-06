"""Small shared projections for business search providers."""

from django.db.models import Q
from django.db.models import Value
from django.db.models.functions import Concat


def person_values(person):
    return (str(person), person.first_name, person.last_name)


def matching_parent_ids(model, parent_field, paths, term, lookup, **filters):
    condition = Q()
    for path in paths:
        condition |= Q(**{f"{path}__{lookup}": term})
    queryset = model.objects.all()
    if len(paths) == 2 and paths[0].endswith("first_name") and paths[1].endswith("last_name"):
        queryset = queryset.annotate(search_full_name=Concat(paths[0], Value(" "), paths[1]))
        condition |= Q(**{f"search_full_name__{lookup}": term})
    return queryset.filter(condition, **filters).values(parent_field)
