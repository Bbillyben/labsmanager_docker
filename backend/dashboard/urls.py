from django.urls import include, path, re_path
from . import views
urlpatterns = [
    path('', views.DashboardView.as_view(), name='dashboard'),
    path('fundloss', views.FundLossView.as_view(), name='loss'),
    path('fundloss/card', views.FundLossCardView.as_view(), name='loss_card'),
    
    path('fundconsumption/card', views.FundConsumptionCardView.as_view(), name='consumption_card'),
    
    path('fundstale', views.fundStaleView.as_view(), name='fundstale'),
    path('fundstale/card', views.fundStaleCardView.as_view(), name='fundstale_card'),
    
    path('contractstale', views.contractstaleView.as_view(), name='contractstale'),
    path('contractstale/card', views.contractstaleCardView.as_view(), name='contractstale_card'),
    
    path('milestones/card', views.MilestonesCardView.as_view(), name='milestones_card'),
    
    path('employee/card', views.IncomminEmployeeCardView.as_view(), name='employee_card'),
    
]
