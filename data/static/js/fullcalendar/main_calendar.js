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
    }
    calendar = $('#calendar-box').lab_calendar(option);
   

}





// ---------------------- filtering function --------------------- //
function getCalenderFilters(){
    var leaveList = $.map($('#leave_type :checkbox:checked'), function(n, i){
                return n.value;
        }).join(',');
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


