from django.utils.translation import gettext_lazy as _
from django.db.models.signals import m2m_changed, pre_save, post_save
from django.db.models import Q
from django.dispatch import receiver

from .models import UserNotification
from endpoints.models import Milestones
from staff.models import Employee
from project.models import Participant


@receiver(m2m_changed, sender=Milestones.employee.through)
def employee_milestones_changed(sender, instance, action, reverse, model, pk_set, **kwargs):
    '''
    Handle the modification in milestones attribution (add or remove employee)
    '''
    if action[:5] == 'post_':
        for employee_id in pk_set:
            emp = Employee.objects.get(pk=employee_id)
            print(f"============== >>>>> Employee {emp} {action[5:8]} to milestone {instance} / is user : {emp.user}")            
            if not emp.user is None:
                UserNotification.add_notification(user=emp.user, instance=instance, action=action[5:8])

@receiver(pre_save, sender=Milestones)
def track_status_change(sender, instance, **kwargs):
    '''
    Handle the modification of milestone's status (whether it's done or not)
    '''
    if instance.pk:  # Vérifiez si l'instance existe déjà (mise à jour)
        old_instance = Milestones.objects.get(pk=instance.pk)
        if old_instance.status != instance.status:
            # print(f"============== >>>>> Status of milestone '{instance.name}' changed from {old_instance.status} to {instance.status}")
            for emp in instance.employee.filter(~Q(user=None)): 
                action="com" if instance.status else "add"
                UserNotification.add_notification(user=emp.user, instance=instance, action=action)
        if old_instance.deadline_date != instance.deadline_date:
            # print(f"============== >>>>> Deadline Date of milestone '{instance.name}' changed from {old_instance.deadline_date} to {instance.deadline_date}")
            message = _("Reschedule from %(old)s to %(new)s")%({'old':old_instance.deadline_date, 'new':instance.deadline_date})
            for emp in instance.employee.filter(~Q(user=None)): 
                UserNotification.add_notification(user=emp.user, instance=instance, action="res", message=message, force=True)
                
@receiver(post_save, sender=Participant)
def track_participant_add(sender, instance, created, **kwargs):
    '''
    Handle the creation of new participant in project
    '''
    if created and not instance.employee.user is None:
        UserNotification.add_notification(user=instance.employee.user, instance=instance, action="add")
    