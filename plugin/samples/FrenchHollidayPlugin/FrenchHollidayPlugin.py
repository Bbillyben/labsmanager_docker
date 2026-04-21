from django.utils.translation import gettext_lazy as _
from django.utils.html import escape

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

def FHP_get_vac_z(*args, **kwargs):
    ''' function to load inderctly the list of choices from files '''
    return FrenchHollidayPlugin.get_vacation_zones_choices()

class FrenchHollidayPlugin(CalendarEventMixin, SettingsMixin, ScheduleMixin, LabManagerPlugin):
    NAME = 'FrenchHollidayPlugin'
    SLUG = 'frenchholliday'
    TITLE = _('French Hollyday Agenda')
    AUTHOR = _('LabsManager contributors/Bbillyben')
    DESCRIPTION = _('Display french vacation in agenda view')
    VERSION = '1.0.2'
    SETTINGS = {
        'FHP_COLOR': {
            'name': _('Background Color'),
            'description': _('background color of events'),
            'default': "#c9e0cf",
            'validator': [RGBColorValidator],
        },
        'FHP_TITLE': {
            'name': _('Add Leave Title'),
            'description': _('add the name of the day off'),
            'default': False,
            'validator': [bool],
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
            'schedule': "W",
        },
    }
    FILTERS={
        "ZONE":{
            "title":_("Vacation Zone Choice"),
            "type":"select",
            "choices":"get_vacation_zones_object",
            "default":"get_default_zone", 
        }
    }
    

    def activate(self):
        """Activate plugin calendarevent.
        """
        logger.debug('[FHP] Activating plugin FrenchHollidayPlugin')
        folder = self.__class__.get_static_folder()
        path = folder / "vac.json"
        if not path.is_file():
            self.__class__.FHP_pull()
        
    def deactivate(self):
        logger.debug(f"[FHP] Start {self.__class__.__name__} deactivation .....")

        folder = Path(self.__class__.get_static_folder())

        if not folder.is_dir():
            return

        delete_count = 0

        vac_file = folder / "vac.json"
        dayoff_file = folder / "dayoff.json"

        for file_path in (vac_file, dayoff_file):
            try:
                if file_path.exists():
                    file_path.unlink()
                    delete_count += 1
            except Exception as exc:
                logger.warning("[FHP] Unable to delete %s: %s", file_path, exc)

        logger.info("[FHP] Deleted %s file(s) from %s", delete_count, folder)
        
    @classmethod
    def get_static_folder(cls):
        return Path(str(settings.MEDIA_ROOT)) / "frenchholliday"
    
    @classmethod
    def FHP_pull(cls):
        logger.debug("[FrenchHollidayPlugin / FHP_pull] starting ...")

        vac_url = "https://data.education.gouv.fr/api/v2/catalog/datasets/fr-en-calendrier-scolaire/exports/json"
        fer_url = "https://calendrier.api.gouv.fr/jours-feries/metropole.json"

        folder = Path(cls.get_static_folder())

        if not folder.exists():
            logger.debug(f"[FHP] create folder {folder}")
            folder.mkdir(parents=True, exist_ok=True)

        def download_and_save_json(url, destination):
            tmp_destination = destination.with_suffix(destination.suffix + ".tmp")

            try:
                req = urllib.request.Request(
                    url,
                    headers={
                        "User-Agent": "LabsManager-FrenchHollidayPlugin/1.0"
                    }
                )

                with urllib.request.urlopen(req, timeout=30) as response:
                    raw_data = response.read()

                text_data = raw_data.decode("utf-8")

                parsed_json = json.loads(text_data)
                with tmp_destination.open("w", encoding="utf-8") as f:
                    json.dump(parsed_json, f, ensure_ascii=False, indent=2)

                tmp_destination.replace(destination)

                logger.info("[FHP] JSON successfully downloaded and saved: %s", destination)
                return True

            except Exception as exc:
                logger.exception("[FHP] ERROR while downloading %s : %s", url, exc)

                if tmp_destination.exists():
                    try:
                        tmp_destination.unlink()
                    except Exception:
                        logger.warning("[FHP] Unable to remove temporary file: %s", tmp_destination)

                return False

        vac_ok = download_and_save_json(vac_url, folder / "vac.json")
        fer_ok = download_and_save_json(fer_url, folder /  "dayoff.json")

        logger.debug(
            "[FrenchHollidayPlugin / FHP_pull] END - vac_ok=%s / fer_ok=%s",
            vac_ok,
            fer_ok
        )
    
    @classmethod
    def get_event(cls, request, event_list):  
        if cls.get_calendar_type(request) in ("project_all", "project", "employee_project"):
            return

        nex_evt = cls.get_vacation_events(request) or []
        event_list.extend(nex_evt)
    
    @classmethod
    def get_filters(cls, request, calendar_type, *args, **kwargs):
        if calendar_type in ["main", "employee"]:
            return super().get_filters(request, args, kwargs)
        return {}
        
    @classmethod   
    def get_vacation_events(cls, request):
        folder = Path(cls.get_static_folder())        
        
        vac_json = cls.load_json_file(folder / "vac.json", default=[])
        dayoff_json = cls.load_json_file(folder / "dayoff.json", default={})
        
        if not isinstance(vac_json, list):
            logger.warning("[FHP] Unexpected format for vac.json: expected list")
            vac_json = []

        if not isinstance(dayoff_json, dict):
            logger.warning("[FHP] Unexpected format for dayoff.json: expected dict")
            dayoff_json = {}    
        
        if "frenchholliday-zone" in request.POST:
            zone = request.POST["frenchholliday-zone"]
        else:
            zone = cls.get_setting(cls(), key="FHP_VACATION_ZONE")
        
        color = cls.get_setting(cls(), key="FHP_COLOR")
        title = cls.get_setting(cls(), key="FHP_TITLE")
        logger.debug(f"[FHP]  vacation event parameters : zone :{zone} / color {color} / title :{title}")
        
        start = datetime.datetime(datetime.MINYEAR, 1, 1)
        end = datetime.datetime(datetime.MAXYEAR, 12, 31)

        if "start" in request.POST:
            raw_start = request.POST.get("start")
            try:
                start = datetime.datetime.strptime(raw_start, "%Y-%m-%dT%H:%M:%SZ")
            except Exception as exc:
                logger.warning(
                    "[FHP] Invalid start date from request skipped: value=%s error=%s",
                    raw_start,
                    exc
                )

        if "end" in request.POST:
            raw_end = request.POST.get("end")
            try:
                end = datetime.datetime.strptime(raw_end, "%Y-%m-%dT%H:%M:%SZ")
            except Exception as exc:
                logger.warning(
                    "[FHP] Invalid end date from request skipped: value=%s error=%s",
                    raw_end,
                    exc
                )
            
        bg_color_vac=color
        bg_color_off=color
        # classname_color_vac="vacation"
        # classname_color_off="dayoff"
        
        start = start.replace(tzinfo=None)
        end = end.replace(tzinfo=None)
        
        data=[]
        unik = set()
        for v in vac_json:
            zone_value = v.get("zones")
            start_value = v.get("start_date")
            end_value = v.get("end_date")
            description = v.get("description")  
            if zone_value  != zone:
                continue
            if not start_value or not end_value or not description:
                logger.warning("[FHP] Incomplete vacation entry skipped: %s", v)
                continue    
            key = (start_value, end_value, zone_value, description)
            
            if key in unik:
                continue
            unik.add(key)
            
            try:
                s = datetime.datetime.strptime(v['start_date'], "%Y-%m-%dT%H:%M:%S%z")
                e = datetime.datetime.strptime(v['end_date'], "%Y-%m-%dT%H:%M:%S%z")

                s = s.replace(tzinfo=None)
                e = e.replace(tzinfo=None)

            except Exception as exc:
                logger.warning(
                    "[FHP] Invalid vacation date format skipped: start=%s end=%s error=%s",
                    v.get('start_date'),
                    v.get('end_date'),
                    exc
                )
                continue
            if (start<=e and s<=end):
                tmp={
                    'start': s.strftime('%Y-%m-%d'),
                    'end': e.strftime('%Y-%m-%d'),
                    'zone': escape(v['zones']),
                    'desc': escape(v['description']),
                    'display': 'background',
                    'color': bg_color_vac,
                    # 'className': classname_color_vac,
                }
                if title:
                    tmp['title'] = (
                        "<span style='color:black;margin-left:0.5em;'>"
                        + escape(v['description'])
                        + "</span>"
                    )
                data.append(tmp)
                
        for item in dayoff_json:
            try:
                d = datetime.datetime.strptime(item, "%Y-%m-%d")
                d = d.replace(tzinfo=None)

            except Exception as exc:
                logger.warning(
                    "[FHP] Invalid dayoff date format skipped: date=%s error=%s",
                    item,
                    exc
                )
                continue
            if (start<=d and d<=end):
                tmp={
                    'start': item,
                    #'end': e.strftime('%Y-%m-%d'),
                    'desc': escape(dayoff_json[item]),
                    'display': 'background',
                    'color': bg_color_off,
                    # 'className': classname_color_off,
                }
                if title:
                    tmp['title'] = (
                        "<span style='color:black;'>"
                        + escape(dayoff_json[item])
                        + "</span>"
                    )
                data.append(tmp)
            
        return  data  
    @classmethod
    def get_vacation_zones_choices(cls):
            folder = Path(cls.get_static_folder())
            path = folder / "vac.json"
            if not path.is_file():
                return []
            vac_json = cls.load_json_file(folder / "vac.json", default=[])
            if not isinstance(vac_json, list):
                logger.warning("[FHP] Unexpected format for vac.json in zone choices")
                return []
            listZone = []
            unik = set()
            for item in vac_json:
                zone = item.get("zones")
                if not zone or zone in unik:
                    continue
                listZone.append((zone, zone))
                unik.add(zone)
            listZone.sort(key=lambda x: x[1])
            return listZone 
    @classmethod
    def get_vacation_zones_object(cls):
        zones = cls.get_vacation_zones_choices() or []
        return {key: value for key, value in zones}
    @classmethod
    def get_default_zone(cls):
        setZone = cls().get_setting("FHP_VACATION_ZONE", backup_value=None)
        return setZone
    @classmethod
    def load_json_file(cls, path, default):
        try:
            with path.open("r", encoding="utf-8") as json_file:
                return json.load(json_file)
        except FileNotFoundError:
            logger.warning("[FHP] JSON file not found: %s", path)
        except json.JSONDecodeError as exc:
            logger.warning("[FHP] Invalid JSON in %s: %s", path, exc)
        except Exception as exc:
            logger.warning("[FHP] Unable to read JSON file %s: %s", path, exc)

        return default
    