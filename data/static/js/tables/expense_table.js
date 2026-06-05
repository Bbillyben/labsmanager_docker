function initialiseExpenseList(target_id = "#project_expense_table", filter_id=null, option = {}){
    console.log("[initialiseExpenseList]",target_id, filter_id, JSON.stringify(option))
    var filters = loadTableFilters(filter_id);
    var default_options={
        url:$(target_id).data("url"),
        name:'expense_list',
        disablePagination:false,
        search:false,
        showColumns:false,
        playCallbackOnLoad:false,
        queryParams: filters,
        
    };
    var filterOption={
            // download:true,
        }
    if(filter_id != null)setupFilterList(filter_id, $(target_id), '#filter-list-'+filter_id,filterOption);


    Object.assign(default_options, option);
    // console.log(JSON.stringify(default_options));
    $(target_id).labTable(default_options);
}
function adminActionExpenseItem(value, row, index, field){
    action = "<span class='icon-left-cell btn-group'>";
    if(this.canChange=='True' || row.has_perm==true)action += "<button class='icon edit btn btn-success' data-form-url='"+Urls['update_expense'](row.pk)+"' data-model='"+row.class_type+"'><i type = 'button' class='fas fa-edit'></i></button>";
    if(this.canDelete=='True')action += "<button class='icon delete btn btn-danger ' data-form-url='"+Urls['delete_expense'](row.pk)+"'><i type = 'button' class='fas fa-trash'></i></button>";
    action += "</span>"
    return action;
}
function expense_list_contractItem(value, row, index, field){
    // console.log('expense_list_contractItem *************************')
    // console.log(' - value : '+JSON.stringify(value))
    // console.log(' - row : '+JSON.stringify(row))
    if ( value == null){
        return "-"
    }
    response = ""
    response += "<strong>"+value.employee.user_name+'</strong>';
    response += '<small><i>  '+value.contract_type+' - '+value.start_date+" # "+value.end_date+"</i></small>"
    return response;
}