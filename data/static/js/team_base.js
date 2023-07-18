var user_id = 0;
var userperms;

function initTeam(userId,  perms){
    user_id=userId;
    userperms=perms;

    // set up bstable with filters
    var filters = loadTableFilters('teams');
    var filterOption={
        download:true,
    }
    var options={
        queryParams: filters,
        name:'teams',        
    }
    setupFilterList('teams', $('#team_main_table'), '#filter-list-team',filterOption);
    $('#team_main_table').labTable(options);

    $('#team_create').labModalForm({
        formURL:Urls['create_team'](),
        addModalFormFunction: team_refresh,
        modal_title:"Create Team",
    })

   
}



function team_refresh(){
    $('#team_main_table').bootstrapTable('refresh');
}



// --------------- formatter admin button
function adminTeamFormatter(value, row, index, field){
    action = "<span class='icon-left-cell btn-group'>";
    if(this.isStaff=='True')action += "<a href='/admin/staff/team/"+row.pk+"/change/'><button class='icon admin_btn btn btn-primary'><i type = 'button' class='fas fa-shield-halved'></i></button></a>"
    if(this.canChange=="True")action += "<button class='icon edit btn btn-success' data-form-url='/staff/team/"+row.pk+"/udpate' ><i type = 'button' class='fas fa-edit'></i></button>";
    if(this.canDelete=="True")action += "<button class='icon delete btn btn-danger ' data-form-url='/staff/team/"+row.pk+"/delete' ><i type = 'button' class='fas fa-trash'></i></button>";
    action += "</span>"
    return action;
  }

