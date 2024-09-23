from django.utils.translation import gettext_lazy as _

from plugin import LabManagerPlugin
from plugin.mixins import SettingsMixin, ScheduleMixin, CalendarEventMixin

from labsmanager.validators import RGBColorValidator
from labsmanager import settings
import json
import datetime
from pathlib import Path       
import os
import urllib.request
import logging
logger = logging.getLogger("labsmanager.plugin")

def FHP_get_vac_z():
    ''' function to load inderctly the list of choices from files '''
    return FrenchHollidayPlugin.get_vacation_zones_choices()

class FrenchHollidayPlugin(CalendarEventMixin, SettingsMixin, ScheduleMixin, LabManagerPlugin):
    NAME = 'FrenchHollidayPlugin'
    SLUG = 'frenchholliday'
    TITLE = _('French Hollyday Agenda')
    AUTHOR = _('LabsManager contributors/Bbillyben')
    DESCRIPTION = _('Display french vacation in agenda view')
    VERSION = '1.0.0'
    SETTINGS = {
        'FHP_COLOR': {
            'name': _('Background Color'),
            'description': _('background color of events'),
            'default': "#c9e0cf",
            'validator': [RGBColorValidator],
        },
        'FHP_VACATION_ZONE': {
            'name': _('French Vacation Zone'),
            'description': _('one of the zone defined for french vacation'),
            'default': 'Zone B',
            'choices': FHP_get_vac_z,
            'type':'choices',
        },
     }
    
    SCHEDULED_TASKS = {
        # Name of the task (will be prepended with the plugin name)
        'FHP_PULL': {
            'func': 'FHP_pull',
            'schedule': "D",
        },
    }

    def activate(self):
        """Activate plugin calendarevent.
        """
        logger.debug('Activating plugin FrenchHollidayPlugin')
        self.__class__.FHP_pull()
        
        
    @classmethod
    def get_static_folder(cls):
        return str(settings.MEDIA_ROOT) +"/frenchholliday"
    
    @classmethod
    def FHP_pull(cls):
        logger.debug("[FrenchHollidayPlugin / pull_vacation_file] starting ...")
        vac_url = "https://data.education.gouv.fr/api/v2/catalog/datasets/fr-en-calendrier-scolaire/exports/json"
        fer_url = "https://calendrier.api.gouv.fr/jours-feries/metropole.json"
        
        folder = cls.get_static_folder()

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
        
        logger.debug("[FrenchHollidayPlugin / pull_vacation_file] END ~~~~~~~~~~~~~~~ ")
        
    @classmethod
    def get_event(cls, request, event_list):
        nex_evt = cls.get_vacation_events(request)
        event_list.extend(nex_evt)
        
    @classmethod   
    def get_vacation_events(cls, request):
        
        folder = cls.get_static_folder()
        path = folder+"/vac.json"
        if not Path(path).is_file():
            return None
            
        with open(path) as json_file:
            file_contents = json_file.read()
        vac_json = json.loads(file_contents)
        
        path = folder+"/dayoff.json"
        if not Path(path).is_file():
            return None
        with open(path) as json_file:
            file_contents = json_file.read()
        dayoff_json = json.loads(file_contents)
        
        zone = __class__.get_setting(__class__(), key="FHP_VACATION_ZONE")
        color = __class__.get_setting(__class__(), key="FHP_COLOR")
        if "start" in request.GET:
            start= request.GET["start"]
            start= datetime.datetime.strptime(start, "%Y-%m-%dT%H:%M:%SZ")
        else:
            start = datetime.datetime(datetime.MINYEAR, 1, 1)
        if "end" in request.GET:
            end = request.GET["end"]
            end= datetime.datetime.strptime(end, "%Y-%m-%dT%H:%M:%SZ")
        else:
            end = datetime.datetime(datetime.MAXYEAR, 12, 31)
            
        bg_color_vac=color
        bg_color_off=color
        # classname_color_vac="vacation"
        # classname_color_off="dayoff"
        
        start = start.replace(tzinfo=None)
        end = end.replace(tzinfo=None)
        
        data=[]
        unik=[]
        for v in vac_json:
            if v['zones'] != zone:
                continue
            if v['start_date'] in unik:
                continue
            unik.append(v['start_date'])
            
            s=datetime.datetime.strptime(v['start_date'], "%Y-%m-%dT%H:%M:%S%z")
            e=datetime.datetime.strptime(v['end_date'], "%Y-%m-%dT%H:%M:%S%z")
            s = s.replace(tzinfo=None)
            e = e.replace(tzinfo=None)
            if (start<=e and s<=end):
                tmp={
                    'start': s.strftime('%Y-%m-%d'),
                    'end': e.strftime('%Y-%m-%d'),
                    'zone': v['zones'],
                    'desc': v['description'],
                    'display': 'background',
                    'color': bg_color_vac,
                    # 'className': classname_color_vac,
                }
                data.append(tmp)
                
        for item in dayoff_json:
            d=datetime.datetime.strptime(item, "%Y-%m-%d")
            d = d.replace(tzinfo=None)
            if (start<=d and d<=end):
                tmp={
                    'start': item,
                    #'end': e.strftime('%Y-%m-%d'),
                    'desc': dayoff_json[item],
                    'display': 'background',
                    'color': bg_color_off,
                    # 'className': classname_color_off,
                }
                data.append(tmp)
            
        return  data  
    @classmethod
    def get_vacation_zones_choices(cls):
            folder = cls.get_static_folder()
            path = folder+"/vac.json"
            if not Path(path).is_file():
                return None
            with open(path) as json_file:
                file_contents = json_file.read()
            vac_json = json.loads(file_contents)
            listZone = []
            unik = []
            for item in vac_json:
                if not item["zones"] in unik:
                    listZone.append((item["zones"], item["zones"]))
                    unik.append(item["zones"])
            listZone.sort(key=lambda x: x[1])
            return listZone 
# def get_vacation_location_choices(cls):
#     folder = cls.get_static_folder()
#     path = folder+"/vac.json"
#     with open(path) as json_file:
#         file_contents = json_file.read()
#     vac_json = json.loads(file_contents)
#     listZone = []
#     unik = []
#     for item in vac_json:
#         if not item["location"] in unik:
#             listZone.append((item["location"], item["location"]))
#             unik.append(item["location"])
#     listZone.sort(key=lambda x: x[1])
#     return listZone
