var user_id;
var api_URL;
var patch_url;
var add_url;
var calendar;
var userperms
function initCalendar(userId, apiURL,patchUrl, addUrl, perms){
    user_id=userId;
    api_URL=apiURL;
    patch_url=patchUrl;
    add_url=addUrl;
    userperms=perms;
    
    Calendar_loadFilters();
    initListener();
    initFullCalendar();
}

function initFullCalendar(){
    const calendarEl = document.getElementById('calendar-box')
    calendar = new FullCalendar.Calendar(calendarEl, {
        timeZone: 'UTC',
        initialView: 'dayGridMonth',
        headerToolbar: {
            left: 'prev,next today',
            center: 'title',
            right: 'dayGridMonth,dayGridWeek,listWeek'
        },
        editable: true,
        events:{
                url: api_URL,
                method: 'GET',
                extraParams:getCalenderFilters,
            },
        selectable: true,
        eventDidMount: function(info) {
            $(info.el).tooltip({
              title: info.event.title,
              placement: 'top',
              trigger: 'hover',
              container: 'body',
            });
          },
        eventDrop: LeaveChangeHandler,
        eventResize: LeaveChangeHandler,
        eventClick: eventClicked,
        select: eventSelectHandler,
    })
    calendar.render()

}

function eventClicked(info){
    $(info.el).tooltip('dispose');
    $('.popover').popover('dispose');
    console.log(info.event)
    titleP ='<div class="d-flex flex-wrap">'
    titleP += "<b>"+info.event.extendedProps.type+"</b>";
    titleP += '<span class="flex" style="flex-grow: 1;"></span>';
    titleP += '<div class="btn-group" role="group">';
    titleP += '<button type="button" id="popover_close" class="btn btn-close close" ></button>',
    titleP += '</div>';
    titleP += '</div>';
    textP = "<em><b>" + info.event.extendedProps.employee + "</b></em>";
    textP += "</br>" + info.event.start.toDateString() + " - " + info.event.end.toDateString();
    if(info.event.extendedProps.comment) textP +="</br><i>"+ info.event.extendedProps.comment+"</i>";
    if(perms.includes("leave.change_leave") || perms.includes("leave.delete_leave") || perms.includes("staff.view_employee")){
        textP +="<hr/>";
        textP +="<div class='d-flex flex-wrap'>";
        //textP +="<span class='btn-group'>";
        if(perms.includes("leave.change_leave"))textP +="<button class='icon edit_leave btn btn-success' data-form-url='/calendar/update/"+info.event.extendedProps.pk+"/' ><i type = 'button' class='fas fa-edit'></i></button>";
        if(perms.includes("staff.view_employee")) textP +="<a href='/staff/employee/"+info.event.extendedProps.employee_pk+"'><button class='icon btn btn-secondary'><i type = 'button' class='fas fa-user'></i></button></a>"; 
        if(perms.includes("is_staff"))textP +="<a href='/admin/leave/leave/"+info.event.extendedProps.pk+"/change/'><button class='icon admin_btn btn btn-primary'><i type = 'button' class='fas fa-shield-halved'></i></button></a>"; 
        textP += '<span class="flex" style="flex-grow: 1;"></span>';
        if(perms.includes("leave.delete_leave"))textP +="<button class='icon delete_leave btn btn-danger ' data-form-url='/calendar/delete/"+info.event.extendedProps.pk+"/' ><i type = 'button' class='fas fa-trash'></i></button>";
        //textP +="</span>";

        textP +="</div>";

    }
    

    $(info.el).popover({
        title: titleP,
        content: textP,
        container: 'body',
        trigger: 'click',
        animation: true,
        html:true,
        placement: 'top',
        delay: { "show": 50, "hide": 50 },
        sanitize  : false,
    });
    // $(info.el).on('shown.bs.popover', function () {
    //     this.onclick = function() { alert($(this).text()); };
    //   });

    $(info.el).popover('show');
    updateLeaveButtonHandler();

}
function updateLeaveButtonHandler(){
    $("#popover_close").click(function(){$('.popover').popover('dispose');})
    $(".edit_leave").each(function () {
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
                successMessage: "Employee deleted",
                dataUrl: '/api/employee/',
                dataElementId: '#employee_main_table',
                dataKey: 'table',
                addModalFormFunction: calendar_refresh,
            }
        });
        $(this).click(function(){$('.popover').popover('dispose');})
    });
    $(".delete_leave").each(function () {
        
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
                addModalFormFunction: calendar_refresh,
            }
        });
        $(this).click(function(){$('.popover').popover('dispose');})
    });
}


// ---------------------- Selection de date  --------------------- //
function eventSelectHandler(info){
    // console.log('Selection de date');
    // console.log(info);
    $('.popover').popover('dispose');

    var d = new Date(info.end);
    d.setDate(d.getDate() - 1)
    modURL=add_url+"?start_date="+info.start.toISOString()+"&end_date="+d.toISOString();
    try{
        //$('#detail-panels').unbind('click');
        $('#calendar-box').modal('dispose');
    }catch (error) {
        console.log(error);
    }
    
    $('#calendar-box').modalForm({
        modalID: "#create-modal",
        modalContent: ".modal-content",
        modalForm: ".modal-content form",
        formURL: modURL,
        isDeleteForm: false,
        errorClass: ".form-validation-warning",
        asyncUpdate: true,
        asyncSettings: {
            directUpdate: true,
            closeOnSubmit: true,
            successMessage: "Employee deleted",
            dataUrl: '/api/employee/',
            dataElementId: '#employee_main_table',
            dataKey: 'table',
            addModalFormFunction: calendar_refresh,
            forceExitFunction: true,
        }
    });
     
}
// ---------------------- filtering function --------------------- //
function getCalenderFilters(){
    var leaveList = $.map($('#leave_type :checkbox:checked'), function(n, i){
                return n.value;
        }).join(',');
    console.log(leaveList)
    filters={
        type:leaveList
    };
    return filters
}

// load & Save
function Calendar_loadFilters(){
    // load filters values => see in js.labsmanager.filters.loadTableFilters
    var filters=loadTableFilters("calendar-filter");

    // types filters
    if ('type' in filters){
        var types =filters['type'].split(",");
        $('#leave_type :checkbox').each(function(){
            $(this).prop("checked", types.includes(this.value))
        });
    }
    // other filters to come
}
// ------ listener
function initListener(){
    $('#leave_type :checkbox').change(function() {   
        // save of filters values => see in js.labsmanager.filters.saveTableFilters
        saveTableFilters("calendar-filter", getCalenderFilters());
        calendar_refresh();
    });
}

function calendar_refresh(){
    //console.log("calendar_refresh")
    $('#calendar-box').unbind('click');
    calendar.refetchEvents();  
}



// -------------------------  Update Event Functions --------------- //
function LeaveChangeHandler(evt){
    //console.log("LeaveChangeHandler called");
    datas=evt['event'];
    ne={};
    ne["pk"]=datas["extendedProps"]["pk"];
    ne["employee"]=datas["extendedProps"]["employee_pk"];
    ne["type"]=datas["extendedProps"]["type_pk"];
    ne["start_date"]=datas["start"].toISOString().split('T')[0];
    if(datas["end"]){
        var d = new Date(datas["end"]);
        d.setDate(d.getDate() - 1)
        ne["end_date"]=d.toISOString().split('T')[0];
    }else{
        ne["end_date"]=ne["start_date"];
    }
    //console.log("new Event : "+JSON.stringify(ne));
    // ajax
    var csrftoken = getCookie('csrftoken');
    $.ajax({
        beforeSend: function(xhr) {
            xhr.setRequestHeader('X-CSRFToken', csrftoken);
        },
        headers : {
            'Accept' : 'application/json',
            'Content-Type' : 'application/json'
        },
        url : patch_url+ne["pk"]+"/",
        type : 'PATCH',
        data : JSON.stringify(ne),
        success : function(response, textStatus, jqXhr) {
            //console.log("Event Successfully Patched!");
        },
        error : function(jqXHR, textStatus, errorThrown) {
            // log the error to the console
            console.log("The following error occured: " + textStatus, errorThrown);
        },
        complete : function() {
            calendar.refetchEvents();
        }
    });
}