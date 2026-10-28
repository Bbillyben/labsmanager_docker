"""Demonstrate an external plugin that owns its Django app and migrations."""

from plugin import LabManagerPlugin
from plugin.mixins import ModelMixin, UIContributionMixin


class ModelExample(ModelMixin, UIContributionMixin, LabManagerPlugin):
    NAME = "ModelExample"
    SLUG = "modelexample"
    TITLE = "Model Example"
    DESCRIPTION = "Example of persistent models owned by an external plugin."
    AUTHOR = "LabsManager"
    VERSION = "1.0.0"
    DJANGO_APP = "plugins.ModelExample.apps.ModelExampleConfig"

    UI_CONTRIBUTIONS = [
        {"id": "example-page", "slot": "plugin.page", "type": "page",
         "label": "Model Example", "module": "main", "component": "Page", "api_version": 1},
        {"id": "employee-tab", "slot": "employee.detail.tabs", "type": "tab",
         "label": "Model Example", "module": "main", "component": "EmployeeTab", "api_version": 1},
    ]
