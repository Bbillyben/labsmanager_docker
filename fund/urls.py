from django.urls import include, path, re_path
from . import views, views_modal

urlpatterns = [
    # path('', views.ProjectIndexView.as_view(), name='project_index'),
    # path('<pk>', views.ProjectView.as_view(), name='project_single'),
    path('<pk>/fundoverview/', views.get_fund_global_overview, name='fund_overview_single'),
    path('<pk>/expense_timepoint/', views.get_fundExpenseTimepoint_table, name='fund_overview_single'),
    path('project_recette_graph/<pk>/', views.RecetteGraphView.as_view(), name='graph_recette_project'),
    
    # for sub template 
    path('ajax/<pk>/items/', views.get_fundItem_table, name='fund_item_table'),  # get fund item table template from Fund pk
]

#  for ajax
# urlpatterns += [
#     re_path(r'[a-z]ajax/', ajax_project, name='ajax_project'),
# ]

# for modal

urlpatterns += [
    path('ajax/funditem/add/<fund>', views_modal.FundItemCreateView.as_view(), name='add_funditem_open'),  
    path('ajax/funditem/<pk>/update', views_modal.FundItemUpdateView.as_view(), name='update_funditem_open'),  
    path('ajax/funditem/<pk>/delete', views_modal.FundItemDeleteView.as_view(), name='add_funditem_open'),
    
    path('ajax/add/<project>', views_modal.FundCreateView.as_view(), name='add_fund_open'),  
    path('ajax/<pk>/update', views_modal.FundUpdateView.as_view(), name='update_fund_open'),  
    path('ajax/<pk>/delete', views_modal.FundDeleteView.as_view(), name='add_fund_open'),
    
    path('ajax/expense_timepoint/add/<fund>', views_modal.ExpenseTimepointCreateView.as_view(), name='add_fundexpensetimepoint_open'),
    path('ajax/expense_timepoint/<pk>/update', views_modal.ExpenseTimepointUpdateView.as_view(), name='add_fundexpensetimepoint_open'),
    path('ajax/expense_timepoint/<pk>/delete', views_modal.ExpenseTimepointDeleteView.as_view(), name='add_fundexpensetimepoint_open'), 
    
    path('finder', views.FundFinderView.as_view(), name='fund_finder'), 
    path('ajax/budget/add/project/<project>', views_modal.BudgetCreateView.as_view(), name='add_budget_project'),
    path('ajax/budget/add/employee/<employee>', views_modal.BudgetCreateView.as_view(), name='add_budget_employee'),
    path('ajax/budget/add/team/<team>', views_modal.BudgetCreateView.as_view(), name='add_budget_team'),
    path('ajax/budget/<pk>/update', views_modal.BudgetUpdateView.as_view(), name='update_budget'),
    path('ajax/budget/<pk>/delete', views_modal.BudgetDeleteView.as_view(), name='delete_budget'),
    
    path('ajax/contribution/add/project/<project>', views_modal.ContributionCreateView.as_view(), name='add_contribution_project'),
    path('ajax/contribution/add/employee/<employee>', views_modal.ContributionCreateView.as_view(), name='add_contribution_employee'),
    path('ajax/contribution/add/team/<team>', views_modal.ContributionCreateView.as_view(), name='add_contribution_team'),
    path('ajax/contribution/<pk>/update', views_modal.ContributionUpdateView.as_view(), name='update_contribution'),
    path('ajax/contribution/<pk>/delete', views_modal.ContributionDeleteView.as_view(), name='delete_contribution'),
    
    
    path('ajax/costtype/add', views_modal.CostTypeCreateView.as_view(), name="add_costtype"),
    path('ajax/costtype/<pk>/update', views_modal.CostTypeUpdateView.as_view(), name="update_costtype"),
    
    path('ajax/fundinstitution/add', views_modal.FundInstitutionCreateView.as_view(), name="add_fundinstitution"),
    path('ajax/fundinstitution/<pk>/update', views_modal.FundInstitutionUpdateView.as_view(), name="update_fundinstitution"),
]