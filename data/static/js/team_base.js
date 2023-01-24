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
        callback:updateTeamTableButton,
        
    }
    setupFilterList('teams', $('#team_main_table'), '#filter-list-team',filterOption);
    $('#team_main_table').labTable(options);

   
}



function team_refresh(){
    $('#team_main_table').labTable('refresh');
}


// update admi button
function updateTeamTableButton(){
    $(".edit_team").each(function () {
        //console.log("updateProjectTable :"+this);
        $(this).unbind('click');
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
                addModalFormFunction: team_refresh,
            }
        });
    });
    $(".delete_team").each(function () {
        $(this).unbind('click');
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
                addModalFormFunction: team_refresh,
            }
        });
    });
}


// --------------- formatter admin button
function adminTeamFormatter(value, row, index, field){
    action = "<span class='icon-left-cell btn-group'>";
    if(this.isStaff=='True')action += "<a href='/admin/staff/team/"+row.pk+"/change/'><button class='icon admin_btn btn btn-primary'><i type = 'button' class='fas fa-shield-halved'></i></button></a>"
    if(this.canChange=="True")action += "<button class='icon edit_team btn btn-success' data-form-url='/staff/team/"+row.pk+"/udpate' ><i type = 'button' class='fas fa-edit'></i></button>";
    if(this.canDelete=="True")action += "<button class='icon delete_team btn btn-danger ' data-form-url='/staff/team/"+row.pk+"/delete' ><i type = 'button' class='fas fa-trash'></i></button>";
    action += "</span>"
    return action;
  }

