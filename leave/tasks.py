
import urllib.request
import os
from labsmanager import settings
import logging
logger = logging.getLogger('labsmanager')


def pull_vacation_file():
    logger.debug("[pull_vacation_file] starting ...")
    vac_url = "https://data.education.gouv.fr/api/v2/catalog/datasets/fr-en-calendrier-scolaire/exports/json"
    fer_url = "https://calendrier.api.gouv.fr/jours-feries/metropole.json"
    
    folder = str(settings.MEDIA_ROOT) + "/vacation"

    if not os.path.exists(folder):
        logger.debug(f"create folder {folder}")
        os.makedirs(folder)
    
    try:
        local_filename, headers = urllib.request.urlretrieve(vac_url, folder+"/vac.json")
    except:
        logger.error("ERROR in [pull_vacation_file] / vacation ")
    
    try:
        local_filename, headers = urllib.request.urlretrieve(fer_url, folder+"/dayoff.json")
    except:
        logger.error("ERROR in [pull_vacation_file] / day off ")