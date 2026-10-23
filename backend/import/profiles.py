"""The explicit, permission-scoped catalogue of legacy import Resources."""

from dataclasses import dataclass
import logging
from django.core.exceptions import ImproperlyConfigured
from django.utils.translation import gettext_lazy as _
import tablib

from expense.resources import ExpenseResource, ExpensePointResource
from staff.ressources import EmployeeAdminResource

logger = logging.getLogger("labsmanager")


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


@dataclass(frozen=True)
class PluginImportProfile(ImportProfile):
    plugin: object = None
    method: dict = None

    def metadata(self):
        return {**super().metadata(), "plugin_import": True,
                "plugin_name": str(self.plugin.human_name)}

    def prepare_dataset(self, dataset, option_data=None):
        prepared = self.plugin.prepare_dataset(dataset, self.method, option_data=option_data)
        if not isinstance(prepared, tablib.Dataset):
            raise ValueError("Plugin preparation must return a Dataset")
        return prepared

    def check_eligibility(self, dataset, option_data=None):
        return self.plugin.check_eligibility(dataset, self.method, option_data)

    def transform(self, dataset):
        normalized = self.plugin.normalize_columns(dataset, self.method)
        transformed = getattr(self.plugin, self.method["handler"])(normalized, self.method)
        if not isinstance(transformed, tablib.Dataset):
            raise ValueError("Import handler must return a tablib.Dataset")
        return transformed


def get_profiles():
    """Extend the existing import catalogue through the active plugin registry."""
    from plugin.registry import registry

    profiles = dict(PROFILES)
    resources = {profile.resource_class.__name__: profile for profile in PROFILES.values()}
    for plugin in registry.with_mixin("importmixin"):
        try:
            methods = plugin.get_import_methods()
        except Exception:
            logger.exception("Cannot read import methods from plugin '%s'", plugin.slug)
            continue
        if not isinstance(methods, list):
            logger.warning("Invalid import methods in plugin '%s'", plugin.slug)
            continue
        seen = set()
        for method in methods:
            if not isinstance(method, dict) or not all(isinstance(method.get(key), str) and method[key]
                                                       for key in ("id", "label", "resource", "handler")):
                logger.warning("Invalid import method in plugin '%s'", plugin.slug)
                continue
            if method["id"] in seen:
                logger.warning("Duplicate import method '%s' in plugin '%s'", method["id"], plugin.slug)
                continue
            seen.add(method["id"])
            columns = method.get("columns")
            if not isinstance(columns, dict) or not columns or any(
                not isinstance(name, str) or not name or not isinstance(aliases, list)
                or any(not isinstance(alias, str) or not alias for alias in aliases)
                for name, aliases in columns.items()
            ):
                logger.warning("Invalid columns in plugin '%s'", plugin.slug)
                continue
            target = resources.get(method["resource"])
            if target is None or not callable(getattr(plugin, method["handler"], None)):
                logger.warning("Invalid Resource or handler in plugin '%s'", plugin.slug)
                continue
            key = f"plugin:{plugin.slug}:{method['id']}"
            profiles[key] = PluginImportProfile(
                key, method["label"], f"{plugin.slug} · {target.label}", target.resource_class,
                target.permission, target.identity_columns, target.join_identity,
                formats=("csv", "xlsx", "xls"), template_formats=("xlsx",),
                preview_columns=target.preview_columns, plugin=plugin, method=method,
            )
    return profiles
