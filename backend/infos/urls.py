from django.urls import include, path, re_path
from . import views_modal, views


urlpatterns = [
    # general viewq
    path('', views.OrganizationIndexView.as_view(), name='orga_index'),
    path('institution/<pk>', views.InstitutionView.as_view(), name='institution_single'),
    path('<app>/<model>/<pk>', views.InstitutionView.as_view(), name='orga_single'),
    
    # for sub template 

    path('resume/<app>/<model>/<pk>', views.get_orga_resume, name='orga_resume'),  
    path('info/<app>/<model>/<pk>', views.get_orga_info, name='orga_info'), 


    # for modals
    path('orgainfotype/add/', views_modal.OrganizationInfosTypeFormCreateView.as_view(), name='add_orgainfotype'),
    path('orgainfotype/<pk>/update/', views_modal.OrganizationInfosTypeFormUpdateView.as_view(), name='update_orgainfotype'),  
    
    path('contactinfotype/add/', views_modal.ContactInfoTypeFormCreateView.as_view(), name='add_contactinfotype'),
    path('contactinfotype/<pk>/update/', views_modal.ContactInfoTypeFormUpdateView.as_view(), name='update_contactinfotype'),  
    
    path('contacttype/add/', views_modal.ContactTypeFormCreateView.as_view(), name='add_contacttype'),
    path('contacttype/<pk>/update/', views_modal.ContactTypeFormUpdateView.as_view(), name='update_contacttype'),  
    
    
    path('orgainfo/add/<app>/<model>/<obj_id>/', views_modal.OrganizationInfosCreateView.as_view(), name='add_orgainfo'),
    path('orgainfo/<pk>/update/', views_modal.OrganizationInfosUpdateView.as_view(), name='update_orgainfo'),
    path('orgainfo/<pk>/delete/', views_modal.OrganizationInfosRemoveView.as_view(), name='delete_orgainfo'),
    
    
    path('orgacontact/add/<app>/<model>/<obj_id>/', views_modal.ContactCreateView.as_view(), name='add_orgacontact'), 
    path('orgacontact/add/<pk>/update/', views_modal.ContactUpdateView.as_view(), name='update_orgacontact'), 
    path('orgacontact/add/<pk>/delete/', views_modal.ContactRemoveView.as_view(), name='delete_orgacontact'), 

    path('contact/<id>/infos/', views.get_orga_contact_info, name='contact_info'), 
    path('contact/<id>/infos/add/', views_modal.ContactInfoCreateView.as_view(), name='add_contact_info'), 
    path('contact/infos/<pk>/update/', views_modal.ContactInfoUpdateView.as_view(), name='update_contact_info'), 
    path('contact/infos/<pk>/delete/', views_modal.ContactInfoRemoveView.as_view(), name='delete_contact_info'), 
    
    path('notes/<app>/<model>/<pk>/template', views.get_generic_infos_template, name='generic_info_template'),
    path('notes/<app>/<model>/<pk>/', views.get_generic_infos, name='generic_info'),
    path('notes/add/<app>/<model>/<obj_id>/', views_modal.GenericNoteCreateView.as_view(), name='add_genericnote'),
    path('notes/<pk>/update/', views_modal.GenericNoteUpdateView.as_view(), name='GenericNoteUpdateView'),
    path('notes/<pk>/delete/', views_modal.GenericNoteRemoveView.as_view(), name='GenericNoteDeleteView'),
]   