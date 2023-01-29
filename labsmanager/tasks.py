
# from django.core.mail import EmailMessage
# from django.template.loader import render_to_string

# from .utils import send_email

# from django.contrib.auth import get_user_model 

import logging
logger = logging.getLogger('labsmanager')

def testSched():
    logger.debug("######### this is a test")

def sendMailTest():    
    logger.debug("[send_email_test] starting")
    
    # logger.debug("  - args :"+str(args))
    # logger.debug("  - kwargs :"+str(kwargs))
    
    # User = get_user_model()
    # users = User.objects.all()
    # emailadress=kwargs["recipient"]
    
    
    # contextEmail={users:users,}
    # html_content = render_to_string('email/user_list.html',context=contextEmail)
    
    # logger.debug("  - emailadress :"+str(emailadress))
    # logger.debug("  - html_content :"+str(html_content))
    # return html_content
    # resp=send_email(
    #     subject="Test Email", 
    #     body="",
    #     recipients=emailadress,
    #     from_email=None,
    #     html_message=html_content
    #     )
    
    