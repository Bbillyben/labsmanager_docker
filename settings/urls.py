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
    
    
    
    path('subscriptions_setting', views.Subscription_List.as_view(), name='subscriptions_setting'),
    path('favorites_setting', views.Favorite_List.as_view(), name='favorite_setting'),
    
    path('employee_user_setting', views.EmployeeUser_list.as_view(), name='employee_user_setting'),
    
]

