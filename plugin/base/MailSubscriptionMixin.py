
import os
from settings.accessor import get_global_setting
import logging
logger = logging.getLogger("labsmanager.plugin")
class MailSubscriptionMixin:
    '''
    Mixin to add context data to subscription mail 
    send as well as template (subdir tempaltes/[slug]/mytemplate.html)
    the template will be added at the bottom of the mail, before the footer
    context data will be accessible by [mypugin-slug].mydata
    '''
    TEMPLATE_FILE = "plugin_template.html"  # report here the name of the template. ie : 'mytemplate.html' 
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
        """
        Add extra context data to report 
        Args: 
            * user : the user for whom the mail will be sent
            * current_context : a copy the current context for rendering (do not alterate, useless, just for informations purpose)
        datas will be added to the global email context accessible by plugin's [slug]
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
        '''
        use in mail template to collect templatefilename to user
        perform some verification to prevent errors in template rendering
        avoid overriding this method.
        '''
        pgI = cls()
        if len(pgI.TEMPLATE_FILE) <1:
            logger.warning(f"[MailSubscriptionMixin] : {pgI.name} do not have template file parametered")
            return False
        tempPath = pgI.slug+"/"+pgI.TEMPLATE_FILE
        testPath = os.path.join(pgI.path(), 'templates', tempPath)        
        if os.path.isfile(testPath):
            return tempPath
        logger.warning(f"[MailSubscriptionMixin] : {pgI.name} / {pgI.TEMPLATE_FILE} not found at {testPath}")
        return False