"""The explicit, permission-scoped catalogue of legacy import Resources."""

from dataclasses import dataclass
from django.core.exceptions import ImproperlyConfigured
from django.utils.translation import gettext_lazy as _

from expense.resources import ExpenseResource, ExpensePointResource
from staff.ressources import EmployeeAdminResource


@dataclass(frozen=True)
class ImportProfile:
    key: str
    label: object
    description: object
    resource_class: type
    permission: str
    identity_columns: tuple[str, ...] = ()
    join_identity: bool = False
    formats: tuple[str, ...] = ("csv", "tsv", "xls", "xlsx")
    template_formats: tuple[str, ...] = ("csv", "xlsx")
    preview_columns: tuple[str, ...] = ()

    def allowed(self, user):
        return user.is_authenticated and user.has_perm(self.permission)

    def metadata(self):
        resource = self.resource_class()
        return {
            "key": self.key,
            "label": str(self.label),
            "description": str(self.description),
            "formats": self.formats,
            "template_formats": self.template_formats,
            "preview_columns": [{"key": name, "label": str(field.column_name)}
                                for name, field in self.preview_fields(resource)],
        }

    def preview_fields(self, resource):
        fields = []
        for name in self.preview_columns:
            if name not in resource.fields:
                raise ImproperlyConfigured(
                    f"Import profile '{self.key}' references unknown preview field '{name}'"
                )
            fields.append((name, resource.fields[name]))
        return fields


# The historical /import/ view requires common.import for all four Resources.
# Keep a permission on each profile so a future profile can choose its own rule.
PROFILES = {
    profile.key: profile for profile in (
        ImportProfile("expense", _("Expenses"), _("Import individual expenses"), ExpenseResource,
                      "common.import", identity_columns=("Expense Id", "id"),
                      preview_columns=( "desc", "type", "amount", "project",
                                       "fund", "funder", "institution", "date")),
        ImportProfile("employee", _("Employees"), _("Import employees"), EmployeeAdminResource,
                      "common.import", identity_columns=("First Name", "Last Name"), join_identity=True),
        ImportProfile("expense-timepoint", _("Expense timepoints"), _("Import expenses by type"), ExpensePointResource,
                      "common.import", identity_columns=("Ref", "type"), join_identity=True),
    )
}
