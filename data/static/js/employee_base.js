

function initialiseBaseEmployee(){

    // initialise table
    var filters = loadTableFilters('employee');
    var filterOption={
        download:true,
    }
    var options={
        post_body_callback:update_base_emp_table,
        url:"/api/employee/",
        queryParams: filters,
        name:'employee',        
    }
    setupFilterList('employee', $('#employee_main_table'), '#filter-list-employee',  filterOption);


    $('#employee_main_table').labTable(options);

    $("#employee_create").labModalForm({
        formURL:  Urls['create_employee'](),
        addModalFormFunction: function(){$('#employee_main_table').bootstrapTable('refresh');},
    })
}

function update_base_emp_table(){
    $("#employee_main_table").find('.show_orgchart').each(function(){
        $(this).labModal({
            templateURL: Urls['employee_org_chart_modal']($(this).data("emp_pk")),
            modal_title:"Employee Organisation",
        })

    })
    $("#employee_main_table").find('.show_teamlead').each(function(){
        $(this).labModal({
            templateURL: Urls['empl_team_lead']($(this).data("emp_pk")),
            modal_title:"Employee Teams",
        })

    })
    
}















