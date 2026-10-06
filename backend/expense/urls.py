from django.urls import include, path, re_path
from . import views, views_modal

urlpatterns = [
    path('', views.ContractIndexView.as_view(), name='contract_index'),
    # path('<pk>', views.ProjectView.as_view(), name='project_single'),
    path('project_expense_graph/<pk>/', views.ExpenseGraphView.as_view(), name='graph_expense_project'),
    
    
    # for sub template 
    path('ajax/<pk>/contract_expense/', views.get_contractExpense_table, name='contract_expense_table'),  # get fund item table template from Fund pk
]

# for modal

urlpatterns += [
    path('ajax/contract/add/', views_modal.ContractCreateView.as_view(), name='add_contract'), 
    path('ajax/contract/add/employee/<employee>', views_modal.ContractCreateView.as_view(), name='add_contract_open'), 
    path('ajax/contract/add/project/<project>', views_modal.ContractCreateView.as_view(), name='add_contract_project'),   
    path('ajax/contract/<pk>/update', views_modal.ContractUpdateView.as_view(), name='update_contract_open'),  
    path('ajax/contract/<pk>/delete', views_modal.ContractDeleteView.as_view(), name='delete_contract_open'),
    
    
    path('ajax/contract_expense/add/<contract>', views_modal.ContractExpenseCreateView.as_view(), name='add_contract_expense'),
    path('ajax/contractitem/<pk>/update', views_modal.ContractExpenseUpdateView.as_view(), name='update_contractitem_open'),  
    path('ajax/contractitem/<pk>/delete', views_modal.ContractExpenseDeleteView.as_view(), name='add_contractitem_open'),
    
    path('ajax/contract_type/add/', views_modal.ContractTypeCreateView.as_view(), name='add_contracttype'),
    path('ajax/contract_type/<pk>/update/', views_modal.ContractTypeUpdateView.as_view(), name='update_contract_type'),
    
    path('expense/<pk>/update/', views_modal.ExpenseUpdateView.as_view(), name='update_expense'),
    path('expense/<pk>/delete/', views_modal.ExpenseDeleteView.as_view(), name='delete_expense'),
    path('expense/add/<fund>', views_modal.ExpenseCreateView.as_view(), name='add_expense'),
    
    path('expense/fund/<fund_id>/sync',views_modal.ConfirmSyncView.as_view(), name="fund_expense_sync" ),
]