function initialize_plugin_list(){
    console.log("THIS IS PLUGIN INIT")
    var filters = loadTableFilters('plugin');
    var filterOption={
        download:false,
    }
    console.log("URLS : "+Urls["api-plugin-list"]())
    var options={
        // callback:update_pg_list,
        url:Urls["api-plugin-list"](),
        queryParams: filters,
        name:'plugin',        
    }
    setupFilterList('plugin', $('#plugin-table'), '#filter-list-plugin',  filterOption);


    $('#plugin-table').labTable(options);
}
function update_pg_list(){
    $('#plugin-table').bootstrapTable('refresh');
}

/*   FOrmatters   */
function pg_name_formatter(value, row, index, field){
    response = ""
    if(row.active){
        response +='<i class="fa fa-check-circle fa-w-16 icon-green"></i>';
    }else{
        response +='<i class="fa fa-question-circle fa-w-16"></i>';
    }
    response += '<span class="pg-name">'+value+"</span>";
    if(row.is_builtin){
        response += '<span class="badge bg-success rounded-pill badge-right" >'+"builtin"+"</span>";
    }

    return response;
}