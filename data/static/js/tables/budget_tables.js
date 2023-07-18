var callbackBudget;
var tableBudgetType;
var tableBudgetPk;
function initializeBudgetTable(callback=null){
    callbackBudget=callback;

    tableBudgetType=$("#budget_table").data("type")
    tableBudgetPk=$("#budget_table").data("pk")
  
    var filters = loadTableFilters('budget');
    var filterOption={
        download:true,
    }
    var options={
        queryParams: filters,
        name:'budget',
        
    } 
    if(callbackBudget!=null)options['callback']=callbackBudget;

    setupFilterList('budget', $('#budget_table'), '#filter-list-budget',filterOption);
    $('#budget_table').labTable(options);


    switch (tableBudgetType) {
        case 'project':
          urlmodal=Urls['add_budget_project'](tableBudgetPk);
          break;
        case 'employee':
            urlmodal=Urls['add_budget_employee'](tableBudgetPk);
            break;
        case 'team':
            urlmodal=Urls['add_budget_team'](tableBudgetPk);
            break;
        case 'search':
            urlmodal=false;
            break;
        default:
            urlmodal=false;
          console.log(`[initializeBudgetTable] type not found : ${tableBudgetType}`);
      }
      if(urlmodal && $('#add_budget').length){
            // button ajout
            $('#add_budget').labModalForm({
                formURL:urlmodal,
                addModalFormFunction: updateFullBudget,
                modal_title:"Add",
            })
      }
    

}
function updateFullBudget(){
    $('#budget_table').bootstrapTable('refresh');
}

function adminActionbudget(value, row, index, field){
    action = "<span class='icon-left-cell btn-group'>";
    if(this.isStaff=='True')action += "<a href='"+Urls["admin:fund_budget_change"](row.pk)+"'><button class='icon admin_btn btn btn-primary'><i type = 'button' class='fas fa-shield-halved'></i></button></a>"
    if(this.canChange=='True')action += "<button class='icon edit btn btn-success' data-form-url='"+Urls['update_budget'](row.pk)+"' ><i type = 'button' class='fas fa-edit'></i></button>";
    if(this.canDelete=='True')action += "<button class='icon delete btn btn-danger ' data-form-url='"+Urls['delete_budget'](row.pk)+"' ><i type = 'button' class='fas fa-trash'></i></button>";
    action += "</span>"
    return action;
}