
from datetime import datetime, date, datetime, timedelta
from dateutil.relativedelta import relativedelta
from settings.models import LMUserSetting
# from datetime import date, datetime, timedelta

def getDashboardTimeSlot(request):
    """Return the date range used by a Dashboard widget."""
    if not request.user:
        return {}
    
    pastMonth = LMUserSetting.get_setting('DASHBOARD_FUND_STALE_FROM_MONTH',user=request.user)
    nextMonth= LMUserSetting.get_setting('DASHBOARD_FUND_STALE_TO_MONTH',user=request.user)
    now = datetime.now()
    slot={}
    if pastMonth:
        slot["from"] =getDateToStale(-pastMonth) # now + relativedelta(months=-pastMonth)
    if nextMonth and nextMonth > 0:
        slot["to"]=getDateToStale(nextMonth) # now + relativedelta(months=+nextMonth)
    
    return slot

def getDashboardMilestonesTimeSlot(request):
    """Return the Milestone window selected by Dashboard settings."""
    if not request.user:
        return {}
    
    pastMonth = LMUserSetting.get_setting('DASHBOARD_MILESTONES_STALE_FROM_MONTH',user=request.user)
    nextDays= LMUserSetting.get_setting('DASHBOARD_MILESTONES_STALE_TO_DAYS',user=request.user)
    now = datetime.now()
    slot={}
    if pastMonth:
        slot["from"] =getDateToStale(-pastMonth)
    if nextDays and nextDays > 0:
        slot["to"]=datetime.now() + timedelta(days=nextDays)
    
    return slot   

def getDashboardContractTimeSlot(request):
    """Return the Contract window selected by Dashboard settings."""
    if not request.user:
        return {}
    nextMonth= LMUserSetting.get_setting('DASHBOARD_CONTRACT_STALE_TO_MONTH',user=request.user)
    now = datetime.now()
    slot={}
    if nextMonth and nextMonth > 0:
        slot["to"]=getDateToStale(nextMonth)
    
    return slot    

def getDateToStale(monthToGo):
    """Calculate the date at which an item is considered stale."""
    return datetime.now()+ relativedelta(months=+monthToGo)

def getCurrentMonthTimeslot():
    # Obtenir la date du premier jour du mois courant
    """Return the current calendar month bounds."""
    start_date = date.today().replace(day=1)
    next_first = (start_date + timedelta(days=32)).replace(day=1)
    date_fin = (next_first - timedelta(days=1))
    slot={
        'from':start_date,
        'to':date_fin
    }
    return slot

def get30daysTimeslot():
    """Return a rolling thirty-day window."""
    start_date = date.today() - timedelta(days=1)
    date_fin = (start_date + timedelta(days=31))
    slot={
        'from':start_date,
        'to':date_fin
    }
    return slot

def getdaysTimeslot(fromDelta=-1, toDelta=31):
    """Return a rolling window of the requested number of days."""
    start_date = date.today() + timedelta(days=fromDelta)
    date_fin = date.today() + timedelta(days=toDelta)
    slot={
        'from':start_date,
        'to':date_fin
    }
    return slot
