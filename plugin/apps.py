from django.apps import AppConfig


from django.apps import AppConfig

# from maintenance_mode.core import set_maintenance_mode

from labsmanager.ready import canAppAccessDatabase, isInMainThread, isInWorkerThread
from .registry import registry



import logging
logger = logging.getLogger('labsmanager.plugin')

class PluginConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'plugin'
        
    def ready(self):
        """The ready method is extended to initialize plugins."""
        # skip loading if we run in a background thread
        logger.debug("...... Start Pulgin Initialisation  .....")
        if not isInMainThread() and not isInWorkerThread():
            return

        if not canAppAccessDatabase(
            allow_test=True, allow_plugins=True, allow_shell=True
        ):
            logger.info('Skipping plugin loading sequence')  # pragma: no cover
        else:
            logger.info('Loading LabsManager plugins')

            if not registry.is_loading:
            #     # this is the first startup
            #     try:
            #         from settings.models import LabsManagerSetting

            #         if LabsManagerSetting.get_setting(
            #             'PLUGIN_ON_STARTUP', create=False, cache=False
            #         ):
            #             # make sure all plugins are installed
            #             registry.install_plugin_file()
            #     except Exception:  # pragma: no cover
            #         pass

                # Perform a full reload of the plugin registry
                registry.reload_plugins(
                    full_reload=True, force_reload=True, collect=True
                )
                logger.info('... End Loading Plugin')  # pragma: no cover
                # drop out of maintenance
                # makes sure we did not have an error in reloading and maintenance is still active
                # set_maintenance_mode(False)
