
from django.db.models import Q
from datetime import datetime
from django.core.mail import send_mail
from labsmanager import settings


def str2bool(text, test=True):
    """Test if a string 'looks' like a boolean value.
    Args:
        text: Input text
        test (default = True): Set which boolean value to look for
    Returns:
        True if the text looks like the selected boolean value
         Credit : Inventree https://github.com/inventree/InvenTree
    """
    if test:
        return str(text).lower() in ['1', 'y', 'yes', 't', 'true', 'ok', 'on', ]
    else:
        return str(text).lower() in ['0', 'n', 'no', 'none', 'f', 'false', 'off', ]
    

def is_bool(text):
    """Determine if a string value 'looks' like a boolean.
     Credit : Inventree https://github.com/inventree/InvenTree
     """
    if str2bool(text, True):
        return True
    elif str2bool(text, False):
        return True
    else:
        return False
    
    
def getDateFilter():
    now = datetime.now()
    fi = (Q(end_date__gte=now) | Q(end_date=None))
    return fi


## send an email with specified parameters
def send_email(subject, body, recipients, from_email=None, html_message=None):
    from settings.models import LabsManagerSetting
    
    if type(recipients) == str:
        recipients = [recipients]
    
    if from_email == None:
        from_email=settings.EMAIL_SENDER
        
    # get the subject prefix from settings
    subject_prefix=LabsManagerSetting.get_setting("MAIL_OBJECT_PREFIX")
    if subject_prefix:
        subject= subject_prefix+" "+subject
        
    response = send_mail(
        subject,
        body,
        from_email,
        recipients,
        html_message=html_message,
        fail_silently=False,
    )
    return response



# test if 2 date interval overlap
from datetime import datetime

def intervals_overlap(start1, end1, start2, end2):
    # convert the start and end times to datetime objects
    start1 = datetime.strptime(start1, "%Y-%m-%d %H:%M:%S")
    end1 = datetime.strptime(end1, "%Y-%m-%d %H:%M:%S")
    start2 = datetime.strptime(start2, "%Y-%m-%d %H:%M:%S")
    end2 = datetime.strptime(end2, "%Y-%m-%d %H:%M:%S")
    
    # check if the intervals overlap
    if start1 <= end2 and end1 >= start2:
        return True
    else:
        return False
