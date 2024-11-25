from django.urls import include, path, re_path
from . import views

urlpatterns = [
    path('', views.SettingsView.as_view(), name='settings'),
    path('setting_cost_type', views.SettingList_cost_type.as_view(), name='setting_cost_type'),
    path('setting_fund_institution', views.SettingList_fundInstitution_type.as_view(), name='setting_fund_institution'),
    path('setting_contract_type', views.SettingList_Contract_type.as_view(), name='setting_contract_type'),
    path('setting_leave_type', views.SettingList_Leave_type.as_view(), name='setting_leave_type'),
    path('setting_institution', views.SettingList_Institution.as_view(), name='setting_institution'),
    path('setting_employee_type', views.SettingList_Employee_Type.as_view(), name='setting_employee_type'),
    path('setting_genericinfo_type', views.SettingList_GenericInfo.as_view(), name='setting_genericinfo_type'),
    path('setting_genericinfoproject_type', views.SettingList_GenericInfoProject.as_view(), name='setting_genericinfoproject_type'),
    path('setting_organizationinfo_type', views.SettingList_OrganizationInfosType.as_view(), name='setting_organizationinfo_type'),
    path('setting_contactinfo_type', views.SettingList_ContactInfosType.as_view(), name='setting_contactinfo_type'),
    path('setting_contact_type', views.SettingList_ContactType.as_view(), name='setting_contact_type'),
    
    
    path('subscriptions_setting', views.Subscription_List.as_view(), name='subscriptions_setting'),
    path('favorites_setting', views.Favorite_List.as_view(), name='favorite_setting'),
    
    path('employee_user_setting', views.EmployeeUser_list.as_view(), name='employee_user_setting'),
    path('user_invitation_setting', views.InvitationUser_list.as_view(), name='user_invitation_setting'),
    
    
    path('project_settings/<proj>/', views.get_project_setting_modal, name='project_setting'),
    path('invitation/add', views.labInvitationCreateView.as_view(), name='lab_send_invite'),
    
]

