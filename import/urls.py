from django.urls import include, path, re_path

from . import views

urlpatterns = [
    path('', views.ImportViewBase.as_view(), name='import_index'),
    path('funditem/', views.FundItemImportView.as_view(), name='import_funditem'),
    path('funditem/confirm', views.FundItemImportViewConfirmImportView.as_view(), name='import_funditem_confirm'),
]