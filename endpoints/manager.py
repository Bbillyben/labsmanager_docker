from django.db import models
from datetime import datetime, date, timedelta
from dateutil.relativedelta import relativedelta
from django.db.models import Q, Max

class milestones_manager(models.Manager):
    def overdue(self):
        cdate = date.today()
        query = Q(deadline_date__lte=cdate) & Q(status=False)
        return self.get_queryset().filter(query)
    
    def stale(self, days):
        cdate = date.today() + timedelta(days=days)
        query = Q(deadline_date__lte=cdate) & Q(status=False)
        return self.get_queryset().filter(query)
        
        