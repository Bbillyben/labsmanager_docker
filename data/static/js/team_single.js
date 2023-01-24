var user_id = 0;
var team_id = 0;
var userperms;
var calapiURL;
function initTeamSingleView(user_idA, team_idA, permsA, calapiURLA){
    user_id = user_idA;
    team_id = team_idA;
    userperms=permsA;
    calapiURL=calapiURLA;

    updateTeamMateBtnHandler()
    update_team_desc();



}
function updateTeamMateBtnHandler(){
    $('#teammate_create').modalForm({
        modalID: "#create-modal",
        modalContent: ".modal-content",
        modalForm: ".modal-content form",
        formURL: '/staff/teammate/add/?team_pk='+team_id,
        isDeleteForm: false,
        errorClass: ".form-validation-warning",
        asyncUpdate: true,
        asyncSettings: {
            directUpdate: true,
            closeOnSubmit: true,
            successMessage: "TeaMate Updated",
            dataUrl: '/api/employee/',
            dataElementId: '#employee_dec_table',
            dataKey: 'table',
            addModalFormFunction: update_team_desc,
        }
    })
    $(".delete_teammate").each(function () {
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
                addModalFormFunction: update_team_desc,
            }
        });
    });
    initTeamCalendar();

}
function update_team_desc(){
    //window.location.reload();
    //console.log("update_project called :"+project_id);
    csrftoken = getCookie('csrftoken');
    $.ajax({
        type:"POST",
        url: "/staff/team/"+team_id+"/resume",
        data:{
                pk:team_id,
                csrfmiddlewaretoken: csrftoken,
        },
        success: function( data )
        {
            $('#team_desc_table').html(data);
            
        },
        error:function( err )
        {
             $("body").html(err.responseText)
            //console.log(JSON.stringify(err));
        }
    })
    $.ajax({
        type:"POST",
        url: "/staff/team/"+team_id+"/mate",
        data:{
                pk:team_id,
                csrfmiddlewaretoken: csrftoken,
        },
        success: function( data )
        {
            $('#team_mate_table').html(data);  
            updateTeamMateBtnHandler();          
        },
        error:function( err )
        {
             $("body").html(err.responseText)
            //console.log(JSON.stringify(err));
        }
    })    
}


// for calendar
function initTeamCalendar(){
    var canMod=perms.includes("leave.change_leave") || perms.includes("is_staff");
    const calendarEl = document.getElementById('calendar-team-box')
    option={
        selectable:canMod,
        editable:canMod,
        extraParams:{team:team_id},
    }
    calendar = $('#calendar-team-box').lab_calendar(option);
    

}