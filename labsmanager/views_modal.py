from django.http import HttpResponse

class BSmodalDeleteViwGenericForeingKeyMixin():
    ''' Mixin to apply to BSModalDeleteView that handle GenericForeingkey 
    '''
    def get_success_url(self):
        previous = self.request.META.get('HTTP_REFERER')
        return previous
        
    def post(self, *args, **kwargs):
        
        self.object = self.get_object()
        self.object.delete()
        return HttpResponse("okok", status=200)
    
from bootstrap_modal_forms.generic import BSModalFormView
from .forms import ConfirmForm
from django.urls import reverse_lazy
class BSmodalConfirmViewMixin(BSModalFormView):
    template_name="form_confirm_base.html"
    form_class = ConfirmForm
    success_url=reverse_lazy("index")
    
    action_def = "No Action defined"
    hidden_field=[]
    
    hidden_field_initial= None
    def get_initial(self):
        initial = super().get_initial()
        if self.hidden_field_initial:
            for k,v in self.hidden_field_initial.items():
                initial[k]=v
        return initial
        
    def get_context_data(self):
        context = super().get_context_data()
        context["action"] = self.action_def
        return context
    
    def get(self, request, *args, **kwargs):
        print(f"[BSmodalConfirmViewMixin - GET]")
        hidden={}
        for hf in self.hidden_field:
            if hf in kwargs:
                hidden[hf]=kwargs[hf]
        
        self.hidden_field_initial=hidden
        return super().get(request, *args, **kwargs)
    def post(self, request, *args, **kwargs):
        print(f"[BSmodalConfirmViewMixin - POST]")
        for a in args:
            print(f"  - {a}")
        for k,v in kwargs.items():
            print(f"  - {k}:{v}")
        # return super().post(request, *args, **kwargs)
        return self.action(*args,**kwargs)
    
    def action(self, *args, **kwargs):
        raise Exception("action method has to be overriden")