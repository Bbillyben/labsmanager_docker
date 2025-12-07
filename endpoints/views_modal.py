from django.contrib.auth.mixins import LoginRequiredMixin
from django.utils.translation import gettext_lazy as _
from bootstrap_modal_forms.generic import BSModalCreateView, BSModalUpdateView, BSModalDeleteView, BSModalFormView
from django.urls import reverse, reverse_lazy
from django.http import HttpResponse

from . import models
from . import forms

from django.shortcuts import render

import logging
logger = logging.getLogger('labsmanager')
#### Participant
class MilestonesUpdateView(LoginRequiredMixin, BSModalUpdateView):
    model = models.Milestones
    template_name = 'form_validate_base.html'
    form_class = forms.MilestonesModelForm
    success_message = 'Success: Employee was updated.'
    success_url = reverse_lazy('project_index')
    label_confirm = "Confirm"

# remove
class MilestonesDeleteView(LoginRequiredMixin, BSModalDeleteView):
    model = models.Milestones
    template_name = 'form_delete_base.html'
    # form_class = EmployeeModelForm
    success_url = reverse_lazy('employee')
        
    def post(self, *args, **kwargs):
        
        self.object = self.get_object()
        self.object.delete()
        return HttpResponse("okok", status=200)
    
class MilestonesCreateView(LoginRequiredMixin, BSModalCreateView):
    template_name = 'form_base.html'
    form_class = forms.MilestonesModelForm
    success_message = 'Success: Employee was updated.'
    success_url = reverse_lazy('employee_index')
    label_confirm = "Confirm"
    model = models.Milestones

    def get(self, request, *args, **kwargs):
        kw = self.get_form_kwargs()
        initial={}
        if 'pk' in kwargs:
            initial['milestones']= kwargs['pk']
        elif 'project' in kwargs:
            initial['project']= kwargs['project']
        kw['initial'] = initial
        form = self.form_class(**kw)
        
        context = {'form': form}
        return render(request, self.template_name , context)


from endpoints.models import Milestones
from django.utils import timezone
from datetime import timedelta
from labsmanager.views_modal import BSModalViewCheckAjax
### Action view
class multiMilestonesView(BSModalFormView):
    """
        View that adds milestones to the form kwargs in two separate lists:
        
            milestones["preselect"]      - Milestones that should be preselected
            milestones["notpreselect"]   - Milestones that should not be preselected

        The assignment of milestones depends on the attribute `preselect_before`:

            - If `preselect_before` is True, milestones with a deadline date 
            earlier than today are added to "preselect", others to "notpreselect".
            - If `preselect_before` is False, milestones with a deadline date 
            earlier than today are added to "notpreselect", others to "preselect".
        
        This allows forms to distinguish between milestones that should be preselected
        or not based on their deadline relative to the current date.
    """
    preselect_before=False
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['request'] = self.request  # Passer request au formulaire
        return kwargs
    
    def get(self, request, *args, **kwargs):
        pk = kwargs.get("project", None)

        milestones = {
            "notpreselect": [],
            "preselect": [],
        }

        mss = Milestones.objects.filter(project__pk=pk, status=False)
        curr_date = timezone.now().date()

        for ms in mss:
            key = "preselect" if (ms.deadline_date < curr_date) == self.preselect_before else "notpreselect"
            milestones[key].append(ms)

        form = self.form_class(milestones=milestones)
        context = {
            'form': form,
        }
        return render(request, self.template_name, context)

class delayMilestonesView(BSModalViewCheckAjax, multiMilestonesView):
    template_name = 'form_base.html'
    form_class = forms.delayMilestonesForm
    success_message = 'ttk'
    success_url = reverse_lazy('index')
    
    def form_valid(self, form):
        logger.debug("##############################   delayMilestonesView [form_valid]  ###########################################" )
        logger.debug(f" -> is post plugin : {self.is_post_plugin()}")
        if not self.is_post_plugin():
            return super().form_valid(form)
        
        cleaned_data = form.cleaned_data
        quantity = cleaned_data.get('quantity', 0)
        logger.debug(f" - add quantity : {quantity}")
        logger.debug(f" cleaned data : {cleaned_data}")
        # get the selected milestones named : milestones_PK
        selected_milestones = []
        for key, value in cleaned_data.items():
            if key.startswith('milestone_') and value:
                milestone_id = key.split('_')[1]
                selected_milestones.append(milestone_id)
        logger.debug(f" - selected milestones : {selected_milestones}")
        # add quantity day to milestones deadline date
        for milestone in Milestones.objects.filter(pk__in=selected_milestones):
            logger.debug(f" - initial date : {milestone.deadline_date}")
            milestone.deadline_date += timedelta(days=quantity)
            logger.debug(f" ->> new date : {milestone.deadline_date}")
            milestone.save()
        return super().form_valid(form)
    
    
class validateMilestonesView(BSModalViewCheckAjax, multiMilestonesView):
    template_name = 'form_base.html'
    form_class = forms.ValidateMilestonesForm
    success_message = 'ttk'
    success_url = reverse_lazy('index')
    
    preselect_before=True
    def form_valid(self, form):

        if not self.is_post_plugin():
            return super().form_valid(form)
        
        cleaned_data = form.cleaned_data
        # get the selected milestones named : milestones_PK
        selected_milestones = []
        for key, value in cleaned_data.items():
            if key.startswith('milestone_') and value:
                milestone_id = key.split('_')[1]
                selected_milestones.append(milestone_id)
        # update status to True
        Milestones.objects.filter(pk__in=selected_milestones).update(status=True, quotity=1)
        return super().form_valid(form)