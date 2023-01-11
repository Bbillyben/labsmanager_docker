
user_id = 0;
project_id = 0;

function initProjectBaseView(tableurl, user_idA, project_idA){
        
    user_id = user_idA;
    project_id = project_idA;

    var filters = loadTableFilters('project');
    var filterOption={
        download:true,
    }

    var options={
        callback: updateAdminBtnHandler,
        // exportTypes: ['json', 'xml', 'csv', 'txt', 'excel'],
        // exportOptions: {
        //     fileName:"Project_Export", 
        //     ignoreColumn: ["admin_action"]
        // },
        // showExport: 'true', 
        url:tableurl,
        queryParams: filters,
        name:'project',
        
    }
    setupFilterList('project', $('#project_main_table'),'#filter-list-project', filterOption);
    $('#project_main_table').labTable(options);


    // $('#project_main_table').bootstrapTable({
    //     onLoadSuccess: function(){ updateAdminBtnHandler();},
    //     onSearch: function(){ updateAdminBtnHandler();},
    //     onSort: function(){ updateAdminBtnHandler();},
    //     onToggle: function(){ updateAdminBtnHandler();},
    //     onPageChange: function(){ updateAdminBtnHandler();},
    //     }
    // );

    $("#project_create").modalForm({
        modalID: "#create-modal",
        modalContent: ".modal-content",
        modalForm: ".modal-content form",
        formURL: "/project/ajax/add/",
        isDeleteForm: false,
        errorClass: ".form-validation-warning",
        asyncUpdate: true,
        asyncSettings: {
            directUpdate: true,
            closeOnSubmit: true,
            successMessage: "Employee Created",
            dataUrl: '/api/employee/',
            dataElementId: '#employee_main_table',
            dataKey: 'table',
            addModalFormFunction: updateProjectTable,
        }
    });
}


function updateProjectTable(){
    $('#project_main_table').bootstrapTable('refresh');
}
function updateAdminBtnHandler(){
    $(".edit_project").each(function () {
        //console.log("updateProjectTable :"+this);
        $(this).modalForm({
            modalID: "#create-modal",
            modalContent: ".modal-content",
            modalForm: ".modal-content form",
            formURL: $(this).data("form-url"),
            isDeleteForm: false,
            errorClass: ".form-validation-warning",
            asyncUpdate: true,
            asyncSettings: {
                directUpdate: true,
                closeOnSubmit: true,
                successMessage: "Employee Updated",
                dataUrl: '/api/employee/',
                dataElementId: '#employee_main_table',
                dataKey: 'table',
                addModalFormFunction: updateProjectTable,
            }
        });
    });
    $(".delete_project").each(function () {
        $(this).modalForm({
            modalID: "#create-modal",
            modalContent: ".modal-content",
            modalForm: ".modal-content form",
            formURL: $(this).data("form-url"),
            isDeleteForm: true,
            errorClass: ".form-validation-warning",
            asyncUpdate: true,
            asyncSettings: {
                directUpdate: true,
                closeOnSubmit: true,
                successMessage: "Employee deleted",
                dataUrl: '/api/employee/',
                dataElementId: '#employee_main_table',
                dataKey: 'table',
                addModalFormFunction: updateProjectTable,
            }
        });
    });
}

function adminActionFormatter(value, row, index, field){
    action = "<span class='icon-left-cell btn-group'>";
    if(this.isStaff=='True')action += "<a href='/admin/project/project/"+row.pk+"/change/'><button class='icon admin_btn btn btn-primary'><i type = 'button' class='fas fa-shield-halved'></i></button></a>"
    if(this.canChange=="True")action += "<button class='icon edit_project btn btn-success' data-form-url='/project/ajax/"+row.pk+"/udpate' ><i type = 'button' class='fas fa-edit'></i></button>";
    if(this.canDelete=="True")action += "<button class='icon delete_project btn btn-danger ' data-form-url='/project/ajax/"+row.pk+"/delete' ><i type = 'button' class='fas fa-trash'></i></button>";
    action += "</span>"
    return action;
  }

function ProjectFormatter(value, row, index, field){
    response =  '<span class="icon-right-cell"><a href="'+row.pk+'" title="/'+row.ipkd+'/"> '+value+'</a>';
    return response;
}