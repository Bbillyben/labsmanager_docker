
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
        url:tableurl,
        queryParams: filters,
        name:'project',
        
    }
    setupFilterList('project', $('#project_main_table'),'#filter-list-project', filterOption);
    $('#project_main_table').labTable(options);


    $("#project_create").labModalForm({
        formURL:"/project/ajax/add/",
        addModalFormFunction: updateProjectTable,
        modal_title:"Create Project",
    })
}


function updateProjectTable(){
    $('#project_main_table').bootstrapTable('refresh');
}


function adminActionFormatter(value, row, index, field){
    action = "<span class='icon-left-cell btn-group'>";
    if(this.isStaff=='True')action += "<a href='/admin/project/project/"+row.pk+"/change/'><button class='icon admin_btn btn btn-primary'><i type = 'button' class='fas fa-shield-halved'></i></button></a>"
    if(this.canChange=="True")action += "<button class='icon edit btn btn-success' data-form-url='/project/ajax/"+row.pk+"/udpate' ><i type = 'button' class='fas fa-edit'></i></button>";
    if(this.canDelete=="True")action += "<button class='icon delete btn btn-danger ' data-form-url='/project/ajax/"+row.pk+"/delete' ><i type = 'button' class='fas fa-trash'></i></button>";
    action += "</span>"
    return action;
  }

function ProjectFormatter(value, row, index, field){
    response =  '<span class="icon-right-cell"><a href="'+row.pk+'" title="/'+row.ipkd+'/"> '+value+'</a>';
    return response;
}

