"""Declarative ownership of a Django app supplied by a LabsManager plugin."""


class ModelMixin:
    """Declare a stable Django application owned by this plugin.

    The plugin class must directly inherit ``ModelMixin`` and declare literal
    ``SLUG`` (or ``NAME``) and ``DJANGO_APP`` class attributes. ``DJANGO_APP``
    is the dotted path ``<plugin package>.apps.<AppConfig class>``. The package
    must contain ``__init__.py``, ``apps.py``, ``models.py`` and versioned
    ``migrations/``. The AppConfig must declare literal ``name`` equal to the
    plugin package path and a unique, stable ``label``. These declarations are
    read from source during settings construction, before Django setup.

    Once deployed, never rename the package, AppConfig.name or label: Django
    migration dependencies and model references use them. Model registration
    depends on installed code, not the plugin's functional active state.
    Apply migrations explicitly with Django management commands.
    """

    DJANGO_APP = None

    class MixinMeta:
        MIXIN_NAME = "ModelMixin"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.add_mixin("model", True, __class__)
