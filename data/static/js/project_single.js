
var user_id = 0;
var project_id = 0;
var calendar;

function initProjectSingleView(user_idA, project_idA){
        
    let user_id = user_idA;
    let project_id = project_idA;
    //console.log("initProjectSingleView :"+project_id)


    // MOdal for Project edition
    $('#edit-project').labModalForm({
        formURL: '/project/ajax/'+project_id+'/udpate',
        addModalFormFunction: update_project,
        modal_title:"Edit Project",
    })

    var options={
        url:$('#project_participant_table').data("url"),
        name:'participant',
        disablePagination:true,
        search:false,
        showColumns:false,
        
    }
    $('#project_participant_table').labTable(options)


    var options_inst={
        url:$('#project_institution_table').data("url"),
        name:'institution',
        disablePagination:true,
        search:false,
        showColumns:false,
        
    }
    $('#project_institution_table').labTable(options_inst)



    $('#add_participant').labModalForm({
        formURL: '/project/ajax/'+project_id+'/participant/add',
        addModalFormFunction: updateParticipant,
        modal_title:"Add Participant",
    })
    $('#add_institution_participant').labModalForm({
        formURL: '/project/ajax/'+project_id+'/institution/add',
        addModalFormFunction: updateInstitution,
        modal_title:"Add Institution",
    })


    $('#add_fund_temp').labModalForm({
        formURL:'/fund/ajax/add/' + $("#add_fund_temp").data("projectpk"),
        addModalFormFunction: updateFund,
        modal_title:"Add Fund",
    })

    $('#add_contract').labModalForm({
        formURL:'/expense/ajax/contract/add/project/'+project_id,
        addModalFormFunction: updateContract,
        modal_title:"Add Contract",
    })

    $('#export_word').labModalForm({
        formURL: Urls['project_report_generate'](project_id),
        asyncSettings: {directUpdate:true,closeOnSubmit:true,},
        modal_title:"Export Word",
    })

    $('#add-info').labModalForm({
        formURL:  Urls['create_info_project'](project_id),
        addModalFormFunction: update_project_info,
        modal_title:"Add Info",
    })


    update_project();
    update_project_info();
    initProjectCalendar();
    loadProjectGraph();
    


}
// for calendar
function initProjectCalendar(){
    var canMod=USER_PERMS.includes("leave.change_leave") || USER_PERMS.includes("is_staff");
    option={
        selectable:canMod,
        editable:canMod,
        extraParams:{project:project_id},
    }
    calendar = $('#calendar-project-box').lab_calendar(option);
    
    
    
    

}
function updateProjectCalendar(){
    $('#project_leave_item_table').bootstrapTable('refresh');
    calendar.refetchEvents();  
    calendar.refetchResources();  
}

// for dashboard graph
function loadProjectGraph(){
    url=Urls['graph_expense_project']({pk:project_id})
    loadInTemplate(elt=$("#project_expense_graph"),url=url);

    url2=Urls['graph_recette_project']({pk:project_id})
    loadInTemplate(elt=$("#project_recette_graph"),url=url2);
}

// ----------------------  Project Main  ------------------- //
function updateMainButton(){
    $('.project_action').click(function(){

        data_action = $(this).data('action-type');
        item_pk= $(this).data('pk');
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
                update_project();
            },
            error:function( err )
            {
                 $("body").html(err.responseText)
                //console.log(JSON.stringify(err));
            }
        })
    });

    

}
function update_project(){
    //window.location.reload();
    //console.log("update_project called :"+project_id);
    csrftoken = getCookie('csrftoken');
    $.ajax({
        type:"POST",
        url: "/project/ajax/"+project_id+"/resume",
        data:{
                pk:project_id,
                csrfmiddlewaretoken: csrftoken,
        },
        success: function( data )
        {
            $('#project_desc_table').html(data);
            updateMainButton();
            
        },
        error:function( err )
        {
             $("body").html(err.responseText)
            //console.log(JSON.stringify(err));
        }
    })    
    updateGeneralFundOverview();
}


function update_project_info(){
    //window.location.reload();
    csrftoken = getCookie('csrftoken');
    $.ajax({
        type:"POST",
        url: Urls['project_info_table'](project_id),
        data:{
                pk:project_id,
                csrfmiddlewaretoken: csrftoken,
        },
        success: function( data )
        {
            $('#project_info_table').html(data);
            update_info_btn();
        },
        error:function( err )
        {
             $("body").html(err.responseText)
            //console.log(JSON.stringify(err));
        }
    })    
}

function update_info_btn(){
    $(".update_info").each(function () {
        $(this).labModalForm({
            formURL: $(this).data("form-url"),
            addModalFormFunction: update_project_info,
            modal_title:"Update Info",
        })
    });
    $(".delete_info").each(function () {
        $(this).labModalForm({
            formURL: $(this).data("form-url"),
            isDeleteForm: true,
            addModalFormFunction: update_project_info,
            modal_title:"Delete Info",
        })
    });
}

// ----------------------  Participant  ------------------- //

function updateParticipant(){
    $('#project_participant_table').bootstrapTable('refresh');
    updateProjectCalendar();
}
function updateInstitution(){
    $('#project_institution_table').bootstrapTable('refresh');
}

function adminActionParticipant(value, row, index, field){
    action = "<span class='icon-left-cell btn-group'>";
    if(this.canChange=="True")action += "<button class='icon edit btn btn-success' data-form-url='/project/ajax/participant/"+row.pk+"/udpate' ><i type = 'button' class='fas fa-edit'></i></button>";
    if(this.canDelete=="True")action += "<button class='icon delete btn btn-danger ' data-form-url='/project/ajax/participant/"+row.pk+"/delete' ><i type = 'button' class='fas fa-trash'></i></button>";
    action += "</span>"
    return action;
}

// ----------------------  Fund & Fund Item  ------------------- //

// fund general overview
function updateGeneralFundOverview(){
    csrftoken = getCookie('csrftoken');
    $.ajax({
        type:"POST",
        url: project_id+"/fundoverview/",
        data:{
                pk:project_id,
                csrfmiddlewaretoken: csrftoken,
        },
        success: function( data )
        {
            $('#fund_project_overview_detail').html(data);
            updateMainButton();
            
        },
        error:function( err )
        {
             $("body").html(err.responseText)
            //console.log(JSON.stringify(err));
        }
    })    
}





// --------------------- Contract Table