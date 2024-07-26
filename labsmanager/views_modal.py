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