from django.shortcuts import render, HttpResponse

from .models import favorite
from labsmanager.serializers import FavoriteSerialize
from django.contrib.contenttypes.models import ContentType
# Create your views here.

def get_user_fav_obj(request):
    if request.method != 'POST':
        return HttpResponse("okoko", 400)
    type=request.POST.get('type').split('.')
    pk=request.POST.get('pk')
    
    ct= ContentType.objects.get(app_label=type[0], model=type[1])
    fav=favorite.objects.filter(user=request.user, content_type=ct, object_id=pk)
    return render(request, 'favorite_star.html', {"fav":fav})

def get_nav_favorites(request):
    fav=favorite.objects.filter(user=request.user).order_by("content_type")
    
    data={'favorites':FavoriteSerialize(fav, many=True).data}
    return render(request, 'favorite_nav.html', data)

def toggle_favorites(request):
    if request.method != 'POST':
        return HttpResponse("okoko", 400)
    type=request.POST.get('type').split('.')
    pk=request.POST.get('pk')
    
    ct= ContentType.objects.get(app_label=type[0], model=type[1])
    fav=favorite.objects.filter(user=request.user, content_type=ct, object_id=pk)
    
    data={'fav':0}
    if fav:
        fav.delete()
    else:
        f=favorite(user=request.user,
                   content_type=ct,
                    object_id=pk
                   )
        f.save()
        data={'fav':f}
        
        
    return render(request, 'favorite_star.html', data)
    