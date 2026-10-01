from django.shortcuts import render, HttpResponse

from django.utils.translation import gettext_lazy as _

from settings.accessor import get_global_setting
from labsmanager import settings
from django.contrib.auth.decorators import login_required
from django.http import Http404
from .preferences import list_user_favorites, preference_status, resolve_preference_object, set_preference
# Create your views here.

def preference_object(request):
    try:
        app, model = request.POST.get('type', '').split('.')
        from .preferences import preference_types
        for name, spec in preference_types().items():
            if (spec.model._meta.app_label, spec.model._meta.model_name) == (app, model):
                return resolve_preference_object(request.user, name, request.POST.get('pk'))
    except (ValueError, KeyError):
        pass
    raise Http404

@login_required
def get_user_fav_obj(request):
    if request.method != 'POST' or request.POST.get('type', None) == None:
        return HttpResponse("", 400)
    obj = preference_object(request)
    return render(request, 'favorite_star.html', {"fav": preference_status(request.user, obj)["favorite"]})

def get_user_favorite(request):
    data = {}
    for row in list_user_favorites(request.user):
        data.setdefault(row["legacy_group"], []).append({
            "object_name": row["label"], "object_url": row["legacy_url"],
        })
    return data

@login_required
def get_nav_favorites(request):

    data=get_user_favorite(request)
    return render(request, 'favorite_nav.html', {"datas":data})


@login_required
def get_nav_favorites_accordion(request):

    data=get_user_favorite(request)
    return render(request, 'labmanager/index_card_favorite.html', {"datas":data})

@login_required
def toggle_favorites(request):
    if request.method != 'POST':
        return HttpResponse("", 400)
    obj = preference_object(request)
    enabled = not preference_status(request.user, obj)["favorite"]
    return render(request, 'favorite_star.html', {"fav": set_preference(request.user, obj, "favorite", enabled)["favorite"]})


##### For Subscription ####
@login_required
def get_user_subscription_obj(request):
    if request.method != 'POST' or request.POST.get('type', None) == None:
        return HttpResponse("", 400)
    obj = preference_object(request)
    return render(request, 'subscription_bell.html', {"sub": preference_status(request.user, obj)["subscription"]})


@login_required
def toggle_subscription(request):
    if request.method != 'POST':
        return HttpResponse("", 400)
    obj = preference_object(request)
    enabled = not preference_status(request.user, obj)["subscription"]
    return render(request, 'subscription_bell.html', {"sub": set_preference(request.user, obj, "subscription", enabled)["subscription"]})



#### For email list and modification ####
def get_user_emaillist(request):
    return render(request, 'account/email_list.html')


### for email testing / to open in new window ####
from labsmanager.mails import SubscriptionMail
from django.contrib.auth.models import User
def get_test_email(request,*args, **kwargs):

    upk = request.POST["user"]
    user = User.objects.get(pk=upk)

    sm = SubscriptionMail()
    kwargs ={'user':user, 'embedImg':True}
    
    ctx = sm.generate_context(**    kwargs)
    html_message=  sm.render_html(**kwargs)
    
    return HttpResponse(html_message) #{'status': 'success', 'message': _("Mail Generated"), 'content':html_message})

#### For help button ####

def get_help_btn(request,*args, **kwargs):
    display_help =  getattr(settings, "LABSMANAGER_SHOW_HELP", True)
    if not display_help:
        return HttpResponse("")
    
    
    data={
        "links":getattr(settings, "HELP_LINKS", {})
    }
    
    return render(request, 'help_menu.html', data)
