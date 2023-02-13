var user_id;
var calendar;
function initCalendar(userId){
    user_id=userId;
    
    Calendar_loadFilters();
    initListener();
    initFullCalendar();
}

function initFullCalendar(){
    var canMod=USER_PERMS.includes("leave.change_leave") || USER_PERMS.includes("is_staff");
    const calendarEl = document.getElementById('calendar-box')
    option={
        selectable:canMod,
        editable:canMod,
        extraParams:getCalenderFilters,
        filterResourcesWithEvents:$("#resource_event_cb").is(":checked"),
    }
    calendar = $('#calendar-box').lab_calendar(option);
   

}





// ---------------------- filtering function --------------------- //
function getCalenderFilters(){
    var leaveList = $.map($('#leave_type :checkbox:checked'), function(n, i){
                return n.value;
        }).join(',');
    
    var emp_status=$('#employee_status_selector').val();
    if(isNaN(emp_status))emp_status=null
    var showResEvent=$("#resource_event_cb").is(":checked");
    filters={
        type:leaveList,
        emp_status:emp_status,
        showResEvent:showResEvent,
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
    // employee status
    if ('emp_status' in filters){
        var status =filters['emp_status'];
        if(!isNaN(status)){
            $('#employee_status_selector').val(String(status));
        }
        
    }
    // show only resource with event
    if ('showResEvent' in filters){
        var showResEvent =filters['showResEvent'];
        isCk=(showResEvent=="true")
        $('#resource_event_cb').prop("checked",isCk);        
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
    $('#employee_status_selector').change(function() {   
        // save of filters values => see in js.labsmanager.filters.saveTableFilters
        saveTableFilters("calendar-filter", getCalenderFilters());
        calendar_refresh();
    });
    $('#resource_event_cb').change(function() {   
        // save of filters values => see in js.labsmanager.filters.saveTableFilters
        saveTableFilters("calendar-filter", getCalenderFilters());
        calendar.setOption("filterResourcesWithEvents",$("#resource_event_cb").is(":checked"));
        //calendar_refresh();
    });

}

function calendar_refresh(){
    //console.log("calendar_refresh")
    
    $('#calendar-box').unbind('click');
    calendar.refetchEvents();  
    calendar.refetchResources();  
}


