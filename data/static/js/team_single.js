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

    // project table
    // var filters = loadTableFilters('funditem');
    // var filterOption={
    //     download:true,
    // }
    var options={
        //queryParams: {team:team_id},
        name:'teamProject',
        //url:Urls['api:team-projects'](team_id)
        
    }
    //setupFilterList('funditem', $('#fund_main_table'), '#filter-list-funditem',filterOption);
    $('#team_project_table').labTable(options);




}
function updateTeamMateBtnHandler(){
    $('#teammate_create').labModalForm({
        formURL:'/staff/teammate/add/?team_pk='+team_id,
        addModalFormFunction: update_team_desc,
        modal_title:"Add Teammate",
    })
    
    $(".update_teammate").each(function () {
        $(this).labModalForm({
            formURL: $(this).data("form-url"),
            addModalFormFunction: update_team_desc,
            modal_title:"Update Teammate",
        })
    });
    $(".delete_teammate").each(function () {
        $(this).labModalForm({
            formURL: $(this).data("form-url"),
            isDeleteForm: true,
            addModalFormFunction: update_team_desc,
            modal_title:"Delete Teammate",
        })
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
    var canMod=USER_PERMS.includes("leave.change_leave") || USER_PERMS.includes("is_staff");
    option={
        selectable:canMod,
        editable:canMod,
        extraParams:{team:team_id},
    }
    calendar = $('#calendar-team-box').lab_calendar(option);
    

}