"""Stable core/plugin dashboard definitions. No definitions are stored in the DB."""

from dataclasses import dataclass, field
import logging
from typing import Callable
from django.utils.translation import gettext as _
from . import business_sources
from . import financial_sources
from . import timeline_sources
from . import employee_workload_sources

logger = logging.getLogger("labsmanager")


@dataclass(frozen=True)
class DashboardContext:
    context_type: str
    user: object
    context_object: object = None

    @property
    def scope(self):
        """Keep the established source/plugin scope contract unchanged."""
        return self.context_type

    @property
    def object(self):
        """Compatibility accessor for existing plugin providers."""
        return self.context_object

    @property
    def object_id(self):
        return getattr(self.context_object, "pk", None)

    @classmethod
    def personal(cls, user):
        return cls(context_type="user", user=user)

    @classmethod
    def for_object(cls, user, context_object):
        return cls(context_type=context_object._meta.model_name, user=user, context_object=context_object)

    @classmethod
    def for_project(cls, user, project):
        return cls.for_object(user, project)

    @property
    def project(self):
        """Compatibility accessor; new providers should use context_object."""
        return self.context_object if self.context_type == "project" else None


@dataclass
class DataSource:
    key: str
    label: str
    category: str
    supported_scopes: tuple[str, ...]
    compatible_renderers: tuple[str, ...]
    provider: Callable
    available: Callable = lambda context: True
    description: str = ""
    allow_multiple: bool = False
    default_renderer: str = ""
    config_fields: dict = field(default_factory=dict)


@dataclass
class WidgetDefinition:
    key: str
    title: str
    category: str
    renderer_key: str
    source_key: str
    supported_scopes: tuple[str, ...] = ("user",)
    default_size: tuple[int, int] = (4, 3)
    min_size: tuple[int, int] = (2, 2)
    max_size: tuple[int, int] = (24, 24)
    allow_multiple: bool = False
    printable: bool = True
    icon: str = "LayoutDashboard"
    config_fields: dict = field(default_factory=dict)
    available: Callable = lambda context: True


@dataclass
class TemplateWidget:
    source_key: str
    renderer_key: str
    config: dict = field(default_factory=dict)
    title: str = ""
    x: int | None = None
    y: int | None = None
    width: int | None = None
    height: int | None = None


def _links(context, config):
    from labsmanager.api_v1 import get_user_capabilities
    capabilities = get_user_capabilities(context.user)
    links = []
    if capabilities["view_project_list"]:
        links.append({"key": "projects", "label": _("Projects"), "href": "/app/projects/"})
    if capabilities["view_employee_list"]:
        links.append({"key": "employees", "label": _("Employees"), "href": "/app/employees/"})
    return {"items": links}


def _note(context, config):
    return {"message": config.get("message", "")}


CORE_RENDERERS = {
    "kpi": {"label": "Indicator", "config_fields": {}},
    "compact-list": {"label": "Compact list", "config_fields": {}},
    "alert-list": {"label": "Alert list", "config_fields": {}},
    "progress-list": {"label": "Progress list", "config_fields": {}},
    "overview-list": {"label": "Overview list", "config_fields": {}},
    "deadline-list": {"label": "Deadline timeline", "config_fields": {}},
    "contract-list": {"label": "Contract overview", "config_fields": {}},
    "employee-movements": {"label": "Employee movements", "config_fields": {}},
    "task-workload": {"label": "Task workload", "config_fields": {}},
    "timeline-calendar": {"label": "Timeline calendar", "config_fields": {}},
    "calendar-grid": {"label": "Calendar grid", "config_fields": {}},
    "project-portfolio": {"label": "Project portfolio", "config_fields": {}},
    "project-health-bars": {"label": "Project health bars", "config_fields": {}},
    "employee-workload": {"label": "Employee workload", "config_fields": {}},
    "empty": {"label": "Text", "config_fields": {}},
    "line-chart": {"label": "Line chart", "config_fields": {}},
    "data-consistency": {"label": "Data consistency", "config_fields": {}},
}


def _data_consistency(context, config):
    # The React renderer reads the same scoped summary endpoint as the review
    # page, instead of maintaining an independent Dashboard count.
    return {"summary_url": "/api/v1/data-consistency/summary/"}


def _can_manage_data_consistency(context):
    from data_consistency.permissions import can_manage_consistency
    return can_manage_consistency(context.user)

def _choice(label, options, default):
    return {"type": "choice", "label": label, "choices": options, "default": default}


def _bool(label, default=False):
    return {"type": "boolean", "label": label, "default": default}


def _limit():
    return {"type": "integer", "label": "Maximum items", "default": 5, "min": 1, "max": 20}


def _days(label):
    return _choice(label, ["0", "7", "30", "60", "90"], "0")


PROJECT_SCOPE_FIELDS = {
    "project_scope": {"type": "choice", "label": "Project scope",
                      "choices": ["context", "all_visible", "specific_project"]},
    "project_id": {"type": "project", "label": "Project"},
}

MILESTONE_CONFIG_FIELDS = {**PROJECT_SCOPE_FIELDS,
    "scope": _choice("Milestone scope", ["all_visible", "mine", "participated", "managed_projects"], "all_visible"),
    "status": _choice("Status", ["all", "open", "done"], "open"),
    "overdue_only": _bool("Overdue only"), "due_within_days": _days("Due within"), "limit": _limit()}
TASK_CONFIG_FIELDS = {**PROJECT_SCOPE_FIELDS,
    "scope": _choice("Task scope", ["all_visible", "mine", "subordinates", "managed_projects"], "mine"),
    "status": _choice("Status", ["all", "open", "done"], "open"),
    "overdue_only": _bool("Overdue only"), "due_within_days": _days("Due within"), "limit": _limit()}
TIMELINE_CONFIG_FIELDS = {
    "include_tasks": {**_bool("Tasks", True), "group": "sources"},
    "include_milestones": {**_bool("Milestones", True), "group": "sources"},
    "calendar_days": {**_choice("Horizon", ["7", "14", "21", "30", "60"], "14"), "group": "horizon"},
    **{f"tasks_{key}": {**spec, "group": "tasks"} for key, spec in TASK_CONFIG_FIELDS.items()},
    **{f"milestones_{key}": {**spec, "group": "milestones"} for key, spec in MILESTONE_CONFIG_FIELDS.items()},
}


CORE_SOURCES = (
    DataSource("core.links", "Quick links", "General", ("user",), ("compact-list",), _links,
               description="Links available to you", default_renderer="compact-list"),
    DataSource("core.note", "Note", "General", ("user",), ("empty",), _note,
               description="Personal text", allow_multiple=True, default_renderer="empty",
               config_fields={"message": {"type": "string", "label": "Message", "default": "", "max_length": 500}}),
    DataSource("core.data-consistency", "Data consistency", "Administration", ("user",),
               ("data-consistency",), _data_consistency, available=_can_manage_data_consistency,
               description="Review active data consistency issues", default_renderer="data-consistency"),
    DataSource("core.projects", "Visible projects", "Projects", ("user", "project"), ("kpi", "compact-list", "alert-list", "project-portfolio", "project-health-bars"), business_sources.projects,
               description="Projects you can view", allow_multiple=True, default_renderer="project-portfolio",
               config_fields={**PROJECT_SCOPE_FIELDS, "scope": _choice("Project scope", ["all_visible", "participated", "managed"], "all_visible"),
                              "active_only": _bool("Active projects only"), "late_only": _bool("Overdue projects only"), "limit": _limit()}),
    DataSource("core.milestones", "Project milestones", "Projects", ("user", "project"), ("kpi", "compact-list", "alert-list", "deadline-list"), business_sources.milestones,
               description="Upcoming and overdue milestones on visible projects", allow_multiple=True, default_renderer="deadline-list",
               config_fields=MILESTONE_CONFIG_FIELDS),
    DataSource("core.funds", "Visible funds", "Finance", ("user", "project"), ("kpi", "compact-list", "alert-list", "progress-list", "overview-list"), business_sources.funds,
               description="Funding and consumption summaries", allow_multiple=True, default_renderer="overview-list",
               config_fields={**PROJECT_SCOPE_FIELDS, "scope": _choice("Fund scope", ["all_visible", "managed_projects"], "all_visible"),
                              "active_only": _bool("Active funds only"), "ending_within_days": _days("Ending within"), "limit": _limit()}),
    DataSource("core.contracts", "Visible contracts", "Administration", ("user", "project"), ("kpi", "compact-list", "alert-list", "contract-list"), business_sources.contracts,
               description="Contracts requiring attention", allow_multiple=True, default_renderer="contract-list",
               config_fields={**PROJECT_SCOPE_FIELDS, "active_only": _bool("Active HR follow-up only"), "current_only": _bool("Current contracts only"),
                              "stale_only": _bool("Stale contracts only"), "ending_within_days": _days("Ending within"), "limit": _limit()}),
    DataSource("core.employees", "Visible employees", "HR", ("user", "project"), ("kpi", "compact-list", "alert-list", "employee-movements"), business_sources.employees,
               description="Employees and upcoming movements", allow_multiple=True, default_renderer="employee-movements",
               config_fields={**PROJECT_SCOPE_FIELDS, "scope": _choice("Employee scope", ["all_visible", "self", "subordinates"], "all_visible"),
                              "active_only": _bool("Active employees only"),
                              "movement": _choice("Movement", ["all", "arrivals", "departures"], "all"),
                              "within_days": _choice("Within", ["7", "30", "60", "90"], "30"), "limit": _limit()}),
    DataSource("core.employee-workload", "Employee workload", "HR", ("user",), ("employee-workload",),
               employee_workload_sources.workload, description="Project allocation and open planning items",
               allow_multiple=True, default_renderer="employee-workload",
               config_fields={"scope": _choice("Employee scope", ["single", "team", "subordinates"], "single"),
                              "employee_id": {"type": "employee", "label": "Employee"},
                              "team_id": {"type": "team", "label": "Team"},
                              "metric": _choice("Metric", list(employee_workload_sources.METRICS), "project_allocation"),
                              "limit": _limit()}),
    DataSource("core.leaves", "Visible leaves", "HR", ("user",), ("kpi", "compact-list"), business_sources.leaves,
               description="Current or upcoming absences", allow_multiple=True, default_renderer="compact-list",
               config_fields={"scope": _choice("Leave scope", ["all_visible", "mine", "subordinates"], "all_visible"),
                              "upcoming_days": _choice("Upcoming within", ["7", "30", "60", "90"], "30"),
                              "current_only": _bool("Current absences only"), "limit": _limit()}),
    DataSource("core.tasks", "Project tasks", "Work", ("user", "project"), ("kpi", "compact-list", "alert-list", "task-workload"), business_sources.tasks,
               description="Assigned tasks on visible projects", allow_multiple=True, default_renderer="task-workload",
               config_fields=TASK_CONFIG_FIELDS),
    DataSource("core.timeline", "Timeline", "Work", ("user", "project"), ("timeline-calendar", "calendar-grid"), timeline_sources.timeline,
               description="Tasks and milestones on a shared timeline", allow_multiple=True,
               default_renderer="timeline-calendar", config_fields=TIMELINE_CONFIG_FIELDS),
    DataSource("core.financial-advancement", "Financial advancement", "Finance", ("user", "project"),
               ("kpi",), financial_sources.financial_advancement, allow_multiple=True, default_renderer="kpi",
               config_fields=PROJECT_SCOPE_FIELDS),
    DataSource("core.financial-summary", "Spent / total", "Finance", ("user", "project"),
               ("kpi",), financial_sources.financial_summary, allow_multiple=True, default_renderer="kpi",
               config_fields=PROJECT_SCOPE_FIELDS),
    DataSource("core.expense-trend", "Expense evolution", "Finance", ("user", "project"),
               ("line-chart",), financial_sources.expense_trend, allow_multiple=True, default_renderer="line-chart",
               config_fields={**PROJECT_SCOPE_FIELDS,
                              "display": _choice("Display", ["cumulative", "period"], "cumulative"),
                              "group_by": _choice("Group by", ["total", "fund", "cost_type", "institution"], "total"),
                              "months": {"type": "integer", "label": "Period (months)", "default": 24, "min": 1, "max": 120}}),
)
CORE_WIDGETS = (
    WidgetDefinition("core.quick-links", "Quick links", "General", "compact-list", "core.links", default_size=(4, 3)),
    WidgetDefinition("core.note", "Note", "General", "empty", "core.note", allow_multiple=True, config_fields={"message": "string"}),
    WidgetDefinition("core.projects-count", "Visible projects", "Projects", "project-portfolio", "core.projects",
                     supported_scopes=("user", "project"), default_size=(6, 5), min_size=(3, 2), allow_multiple=True),
    WidgetDefinition("core.milestones", "Project milestones", "Projects", "deadline-list", "core.milestones",
                     supported_scopes=("user", "project"), default_size=(6, 5), min_size=(3, 2), allow_multiple=True),
    WidgetDefinition("core.employee-workload", "Employee workload", "HR", "employee-workload", "core.employee-workload",
                     default_size=(6, 4), min_size=(3, 2), allow_multiple=True),
    WidgetDefinition("core.timeline", "Timeline", "Work", "timeline-calendar", "core.timeline",
                     supported_scopes=("user", "project"), default_size=(8, 5), min_size=(3, 2), allow_multiple=True),
    WidgetDefinition("core.funds", "Funding overview", "Finance", "overview-list", "core.funds",
                     supported_scopes=("user", "project"), default_size=(6, 5), min_size=(3, 2), allow_multiple=True),
    WidgetDefinition("core.expense-trend", "Expense evolution", "Finance", "line-chart", "core.expense-trend",
                     supported_scopes=("user", "project"), default_size=(12, 5), min_size=(4, 3), allow_multiple=True),
    WidgetDefinition("core.data-consistency", "Data consistency", "Administration", "data-consistency",
                     "core.data-consistency", default_size=(4, 3), printable=False,
                     available=_can_manage_data_consistency),
)


TEMPLATES = {
    "employee": (
        TemplateWidget("core.employee-workload", "employee-workload", {"scope": "single"}, x=0, y=0, width=2, height=4),
        TemplateWidget("core.milestones", "deadline-list", {"scope": "mine", "due_within_days": "30"}, width=3, height=6),
        TemplateWidget("core.tasks", "task-workload", {"scope": "mine", "status": "open"}, width=3, height=6),
        TemplateWidget("core.timeline", "calendar-grid", {"include_tasks": True, "include_milestones": True,
                                                            "tasks_scope": "mine", "milestones_scope": "mine", "calendar_days": "14"}, width=3, height=6),
        TemplateWidget("core.leaves", "compact-list", {"scope": "mine", "upcoming_days": "30"}, width=3, height=2),
        
        TemplateWidget("core.projects", "compact-list", {"scope": "participated", "active_only": True}, width=3, height=6),
        
    ),
    "leader": (
        TemplateWidget("core.projects", "project-health-bars", {"scope": "managed", "active_only": True}, width=6, height=8),
        TemplateWidget("core.employee-workload", "employee-workload", {"scope": "subordinates", "metric": "project_allocation"}, width=6, height=4),
        TemplateWidget("core.contracts", "contract-list", {"ending_within_days": "30","active_only": True}, width=3, height=4),
        TemplateWidget("core.leaves", "compact-list", {"scope": "subordinates", "upcoming_days": "30"}, width=3, height=4),
        TemplateWidget("core.tasks", "task-workload", {"scope": "managed_projects", "status": "open"}, width=4, height=5),
        TemplateWidget("core.milestones", "deadline-list", {"scope": "managed_projects", "due_within_days": "30"}, width=4, height=5),
        TemplateWidget("core.timeline", "calendar-grid", {"include_tasks": True, "include_milestones": True,
                                                    "tasks_scope": "managed_projects", "milestones_scope": "managed_projects", "calendar_days": "14"}, width=4, height=5),
        TemplateWidget("core.funds", "overview-list", {"scope": "managed_projects", "active_only": True}),        
    ),
    "lab-manager": (
        TemplateWidget("core.funds", "overview-list", {"ending_within_days": "90", "active_only": True}, width=4, height=8),
        TemplateWidget("core.contracts", "contract-list", {"ending_within_days": "90", "active_only": True}, width=4, height=8),
        TemplateWidget("core.employees", "employee-movements", {"movement": "all", "within_days": "90"}, width=4, height=8),
        TemplateWidget("core.milestones", "deadline-list", {"due_within_days": "60"}, width=4, height=8),
        TemplateWidget("core.tasks", "task-workload", {"status": "open"}, width=4, height=8),
        TemplateWidget("core.timeline", "calendar-grid", {"include_tasks": True, "include_milestones": True,
                                                            "tasks_scope": "all_visible", "milestones_scope": "all_visible", "calendar_days": "14"}, width=4, height=8),
        TemplateWidget("core.projects", "project-health-bars", {"scope": "all_visible", "active_only": True}, width=12, height=8),
        TemplateWidget("core.data-consistency", "data-consistency"),
    ),
    "blank": (),
    "project": (
        TemplateWidget("core.projects", "project-health-bars", {"project_scope": "context"}, width=3, height=8),
        TemplateWidget("core.tasks", "task-workload", {"project_scope": "context", "status": "open"}, width=4, height=5),
        TemplateWidget("core.milestones", "deadline-list", {"project_scope": "context", "due_within_days": "30"}, width=4, height=5),
        
        TemplateWidget("core.timeline", "calendar-grid", {"tasks_project_scope": "context", "milestones_project_scope": "context",
                                                    "include_tasks": True, "include_milestones": True, "calendar_days": "14"}),
        TemplateWidget("core.tasks", "task-workload", {"project_scope": "context", "status": "open"}),
        
        TemplateWidget("core.funds", "overview-list", {"project_scope": "context"}),
        TemplateWidget("core.contracts", "contract-list", {"project_scope": "context"}),
        TemplateWidget("core.expense-trend", "line-chart", {"project_scope": "context"}),
    ),
}


def dashboard_registry(context):
    """Resolve core and active plugins; a broken contribution cannot break a dashboard."""
    sources = {item.key: item for item in CORE_SOURCES}
    widgets = {item.key: item for item in CORE_WIDGETS}
    from plugin import registry as plugin_registry
    for plugin in plugin_registry.with_mixin("dashboard", active=True):
        try:
            plugin_sources = list(plugin.get_dashboard_sources(context))
            plugin_widgets = list(plugin.get_dashboard_widgets(context))
            source_keys = [item.key for item in plugin_sources if isinstance(item, DataSource)]
            widget_keys = [item.key for item in plugin_widgets if isinstance(item, WidgetDefinition)]
            if (len(source_keys) != len(plugin_sources) or len(widget_keys) != len(plugin_widgets)
                    or len(set(source_keys)) != len(source_keys) or len(set(widget_keys)) != len(widget_keys)
                    or set(source_keys) & sources.keys() or set(widget_keys) & widgets.keys()
                    or any(not item.compatible_renderers or (item.default_renderer and item.default_renderer not in item.compatible_renderers)
                           for item in plugin_sources)):
                raise ValueError("Duplicate or invalid dashboard key")
            sources.update({item.key: item for item in plugin_sources})
            widgets.update({item.key: item for item in plugin_widgets})
        except Exception:
            logger.exception("Dashboard definitions from plugin %s were ignored", plugin)
    # A source using a locally registered core renderer needs no custom widget class.
    for source in sources.values():
        if any(item.source_key == source.key for item in widgets.values()):
            continue
        renderer = source.default_renderer or source.compatible_renderers[0]
        if renderer in CORE_RENDERERS and renderer in source.compatible_renderers:
            key = source.key if source.key not in widgets else f"{source.key}.widget"
            widgets[key] = WidgetDefinition(
                key=key, title=source.label, category=source.category,
                renderer_key=renderer, source_key=source.key,
                supported_scopes=source.supported_scopes,
                allow_multiple=source.allow_multiple,
            )
    return sources, widgets


def available_definitions(context):
    sources, widgets = dashboard_registry(context)
    available = {}
    for key, definition in widgets.items():
        source = sources.get(definition.source_key)
        if source is None:
            continue
        try:
            if (context.scope in definition.supported_scopes and definition.available(context)
                    and context.scope in source.supported_scopes
                    and definition.renderer_key in source.compatible_renderers
                    and source.available(context)):
                available[key] = definition
        except Exception:
            logger.exception("Dashboard definition %s was unavailable", key)
    return sources, available


def definition_for_template(definitions, item):
    """Resolve a template item by stable keys, including alternate source renderers."""
    matches = (definition for definition in definitions.values() if definition.source_key == item.source_key)
    fallback = None
    for definition in matches:
        if definition.renderer_key == item.renderer_key:
            return definition
        if fallback is None:
            fallback = definition
    return fallback
