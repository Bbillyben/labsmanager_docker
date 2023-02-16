// ----------------------  Common  ------------------- //
employee_id= 0;
user_id= 0;

function initEmployeeSingleView(user_idA, employee_idA){
    employee_id=employee_idA;
    user_id = user_idA;
    

    $('#employee_team_table').bootstrapTable();

    var options_part={
        callback:update_employee,
        url:$('#employee_project_table').data("url"),
        name:'participant',
        disablePagination:true,
        search:false,
        showColumns:false,
    }
    $('#employee_project_table').labTable(options_part);
    
    var options_status={
        url:$('#employee_status_table').data("url"),
        name:'status',
        disablePagination:true,
        search:false,
        showColumns:false,
    }
    $('#employee_status_table').labTable(options_status);

    var filters = loadTableFilters('leave');
    var filterOption={
        download:true,
    }
    var options={
        queryParams: filters,
        name:'leave',
        
    }
    setupFilterList('leave', $('#employee_leave_table'), '#filter-list-leave',filterOption);
    $('#employee_leave_table').labTable(options);

    // MOdal for employee edition
    $('#edit-employee').labModalForm({
        formURL: '/staff/employee/'+employee_id+'/udpate',
        addModalFormFunction: update_employee,
    })

    $('#add-status').labModalForm({
        formURL: '/staff/employee/'+employee_id+'/status/add/',
        addModalFormFunction: update_status,
    })
    $('#add-info').labModalForm({
        formURL:  Urls['create_info_employee'](employee_id),
        addModalFormFunction: update_employee_info,
    })

    $('#add_project').labModalForm({
        formURL:  '/project/ajax/participant/add/'+employee_id,
        addModalFormFunction: updateParticipant,
    })

    $('#add_contract').labModalForm({
        formURL: '/expense/ajax/contract/add/employee/'+employee_id,
        addModalFormFunction: updateContract,
    })

    $('#add_leave').labModalForm({
        formURL:'/calendar/add/employee/'+employee_id+"/",
        addModalFormFunction: updateLeave,
    })

    update_employee();
    update_employee_info();
    //updateLeaveBtnHandler();
}

// ----------------------  Employee  ------------------- //
function update_employee(){
    //window.location.reload();
    csrftoken = getCookie('csrftoken');
    $.ajax({
        type:"POST",
        url: "/staff/ajax/"+employee_id+"/activ",
        data:{
                pk:employee_id,
                csrfmiddlewaretoken: csrftoken,
        },
        success: function( data )
        {
            $('#employee_dec_table').html(data);
            update_activ_btn();
        },
        error:function( err )
        {
             $("body").html(err.responseText)
            //console.log(JSON.stringify(err));
        }
    })    
}

function update_employee_info(){
    //window.location.reload();
    csrftoken = getCookie('csrftoken');
    $.ajax({
        type:"POST",
        url: Urls['employee_info_table'](employee_id),
        data:{
                pk:employee_id,
                csrfmiddlewaretoken: csrftoken,
        },
        success: function( data )
        {
            $('#employee_info_table').html(data);
            update_info_btn();
        },
        error:function( err )
        {
             $("body").html(err.responseText)
            //console.log(JSON.stringify(err));
        }
    })    
}


function update_activ_btn(){
    $('.user_action').click(function(){

        data_action = $(this).data('action-type');
        item_pk= $(this).data('pk');
        user_id = JSON.parse(document.getElementById('user_id').textContent);
        urlAjax= $(this).data('url');
        csrftoken = getCookie('csrftoken');
       

        $.ajax({
            type:"POST",
            url: urlAjax,
            data:{
                    action_type: data_action,
                    pk:item_pk,
                    csrfmiddlewaretoken: csrftoken,
            },
            success: function( data )
            {
                update_employee();
            },
            error:function( err )
            {
                 $("body").html(err.responseText)
                //console.log(JSON.stringify(err));
            }
        })
    });
}

// ----------------------  Status  ------------------- //
function update_status(){
    $('#employee_status_table').bootstrapTable('refresh');

}


function update_info_btn(){
    $(".update_info").each(function () {
        $(this).labModalForm({
            formURL: $(this).data("form-url"),
            addModalFormFunction: update_employee_info,
        })
    });
    $(".delete_info").each(function () {
        $(this).labModalForm({
            formURL: $(this).data("form-url"),
            isDeleteForm: true,
            addModalFormFunction: update_employee_info,
        })
    });
}
function empStatusFormatter(value, row, index, field){
    //console.log('statusFormatter : '+JSON.stringify(value)+" - row : "+JSON.stringify(row) + "  - index :"+index+ " - fiels :"+field+"  # allow :"+this.allow);
    action = "<span class='icon-left-cell btn-group'>";
    if(this.canChange=='True')action += "<button class='icon edit btn btn-success' data-form-url='/staff/status/"+row.pk+"/update/' ><i type = 'button' class='fas fa-edit'></i></button>";
    if(this.canDelete=='True')action += "<button class='icon delete btn btn-danger ' data-form-url='/staff/status/"+row.pk+"/delete/' ><i type = 'button' class='fas fa-trash'></i></button>";
    action += "</span>"
    return action;
}


// ----------------------  table Project  ------------------- //
function updateParticipant(){
    $('#employee_project_table').bootstrapTable('refresh');
    update_employee();
}
function adminActionParticipant(value, row, index, field){
    //console.log(JSON.stringify(row));
    action = "<span class='icon-left-cell btn-group'>";
    if(this.canChange=="True")action += "<button class='icon edit btn btn-success' data-form-url='/project/ajax/participant/"+row.pk+"/udpate' ><i type = 'button' class='fas fa-edit'></i></button>";
    if(this.canDelete=="True")action += "<button class='icon delete btn btn-danger ' data-form-url='/project/ajax/participant/"+row.pk+"/delete' ><i type = 'button' class='fas fa-trash'></i></button>";
    action += "</span>"
    return action;
}

// ----------------------  table Leave  ------------------- //

function updateLeave(){
    $('#employee_leave_table').labTable('refresh');
    //updateLeaveBtnHandler();
}

function adminActionLeave(value, row, index, field){
    //console.log(JSON.stringify(row));
    action = "<span class='icon-left-cell btn-group'>";
    if(this.isStaff=='True')action += "<a href='/admin/leave/leave/"+row.pk+"/change/'><button class='icon admin_btn btn btn-primary'><i type = 'button' class='fas fa-shield-halved'></i></button></a>"

    if(this.canChange=="True")action += "<button class='icon edit btn btn-success' data-form-url='/calendar/update/"+row.pk+"/' ><i type = 'button' class='fas fa-edit'></i></button>";
    
    if(this.canDelete=="True")action += "<button class='icon delete btn btn-danger ' data-form-url='/calendar/delete/"+row.pk+"/' ><i type = 'button' class='fas fa-trash'></i></button>";
    action += "</span>"
    return action;
}

// ----------------------  table Team  ------------------- //


