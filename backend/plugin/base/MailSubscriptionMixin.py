
import os
from settings.accessor import get_global_setting
import logging
logger = logging.getLogger("labsmanager.plugin")
class MailSubscriptionMixin:
    """Add plugin context and optional templates to subscription emails.

    Declare template filenames in ``TEMPLATE_FILES`` under the plugin's
    ``templates/<slug>/`` directory. The mail renderer appends valid plugin
    templates before its footer and stores ``add_context`` results under the
    plugin slug in the rendering context.
    """
    TEMPLATE_FILES = []  # report here the name of the template. ie : 'mytemplate.html' 
                                            # under templates/[slug]/mytemplate.html
                                            # in template, data are accessible by [slug].mydata
    class MixinMeta:
        """Meta options for this mixin."""
        MIXIN_NAME = 'MailSubscription'
        
    def __init__(self):
        """Register mixin."""
        super().__init__()
        self.add_mixin('mailsubscription', True, __class__)
        
    @classmethod
    def add_context(cls, user, current_context):
        """Return plugin-specific template data for a subscription email.

        Args:
            user: Recipient of the email.
            current_context: Copy of the current mail rendering context.

        Returns:
            Data inserted under the plugin slug in the mail context. The
            default contributes an empty dictionary.
        """
        return {}
   
    @classmethod
    def _activate_mixin(cls, registry, plugins, *args, **kwargs):
        """Activate plugin MailSubscription.
        """
        logger.debug('Activating plugin MailSubscription')


    @classmethod
    def _deactivate_mixin(cls, registry, **kwargs):
        """Deactivate all plugin MailSubscription."""
        logger.debug('Deactivating plugin MailSubscription')
    
    @classmethod
    def get_template(cls):
        """Return declared template paths that exist on disk.

        This method instantiates the plugin and validates files under its
        template directory; implementations normally override ``TEMPLATE_FILES``
        instead of this method. Missing templates are logged and omitted.
        """
        pgI = cls()
        print(f">>>>>> {pgI.TEMPLATE_FILES} ")
        if len(pgI.TEMPLATE_FILES) < 1:
            logger.warning(f"[MailSubscriptionMixin] : {pgI.name} n'a pas de fichiers de template paramétrés")
            return []

        valid_templates = []
        for template in pgI.TEMPLATE_FILES:
            tempPath = pgI.slug + "/" + template
            testPath = os.path.join(pgI.path(), 'templates', tempPath)
            if os.path.isfile(testPath):
                valid_templates.append(tempPath)
            else:
                logger.warning(f"[MailSubscriptionMixin] : {pgI.name} / {template} not found at {testPath}")

        return valid_templates
    