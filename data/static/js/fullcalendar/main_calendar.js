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
        extraParams:getCalenderParams,
        filterResourcesWithEvents:$("#ressource_event_radio_box input[name='ressource_event_radio']:checked").val()!='false',
    }
    calendar = $('#calendar-box').lab_calendar(option);
   

}
function initPrintCalendar(options){
    // console.log('[initPrintCalendar]'+JSON.stringify(options))
    var canMod=false;
    const calendarEl = document.getElementById('calendar-box')
    option={
        selectable:false,
        editable:false,
        initialView:options["initialView"],
        extraParams:{
            type:options["type"],
            emp_status:options["emp_status"],
            team:options["team"],
            showResEventRadio:options["showResEventRadio"],
        },
        filterResourcesWithEvents:options["filterResourcesWithEvents"]!='false',

        eventDrop:null,
        eventResize:null,
        eventClick:null,
        select:null,
        useDatePicker:false,
        headerToolbar: {
            left: '',
            center: 'title',
            right: ''
        },

    }
    calendar = $('#calendar-box').lab_calendar(option);
    calendar.gotoDate(options["start"]);

}

function print_main_calendar(printUrl){
    options = {};
    options['initialView']=calendar.view.type;
    var d = calendar.view.activeStart
    options['start']=d.toISOString();
    d = calendar.view.activeEnd
    options['end']=d.toISOString();
    options['filterResourcesWithEvents']=calendar.getOption("filterResourcesWithEvents");
    var extraP = getCalenderParams();
    options['type']=extraP.type;
    options['emp_status']=extraP.emp_status;
    options['team']=extraP.team;
    options["showResEventRadio"]=$("#ressource_event_radio_box input[name='ressource_event_radio']:checked").val();
    // console.log("Print Cal option :"+JSON.stringify(options));
    var csrftoken = getCookie('csrftoken');
    openWindowWithPost(printUrl, options, csrftoken)
}





// ---------------------- filtering function --------------------- //
function getCalenderParams(){
    var leaveList = $.map($('#leave_type :checkbox:checked'), function(n, i){
                return n.value;
        }).join(',');
    
    var emp_status=$('#employee_status_selector').val();
    if(isNaN(emp_status))emp_status=null;
    var team=$('#employee_team_selector').val();
    if(isNaN(team))team=null;

    var radioResEvent = $("#ressource_event_radio_box input[name='ressource_event_radio']:checked").val();
   
    filters={
        type:leaveList,
        emp_status:emp_status,
        team:team,
        showResEventRadio:radioResEvent,
    };
    return filters
}
function getCalenderFilters(){
    var leaveList = $.map($('#leave_type :checkbox'), function(n, i){
                return '"leave_'+n.value+'":' + n.checked ;
        }).join(',');
    
    var emp_status=$('#employee_status_selector').val();
    if(isNaN(emp_status))emp_status=null;
    var team=$('#employee_team_selector').val();
    if(isNaN(team))team=null;

    var radioResEvent = $("#ressource_event_radio_box input[name='ressource_event_radio']:checked").val();
   
    filters={
        type:"{"+leaveList+"}",
        emp_status:emp_status,
        team:team,
        showResEventRadio:radioResEvent,
    };
    return filters
}

// load & Save
function Calendar_loadFilters(){
    // load filters values => see in js.labsmanager.filters.loadTableFilters
    var filters=loadTableFilters("calendar-filter");
    
    // types filters
    if ('type' in filters){
        try {
            var types =JSON.parse(filters['type']);
          } catch (error) {
            console.error(error);
            types={}
          }
        $('#leave_type :checkbox').each(function(){
            if(types["leave_"+this.value]!=undefined && types["leave_"+this.value] ==false ){
                $(this).prop("checked", false)
            }else{
                $(this).prop("checked", true)
            }
            
        });
    }
    // employee status
    if ('emp_status' in filters){
        var status =filters['emp_status'];
        if(!isNaN(status)){
            $('#employee_status_selector').val(String(status));
        }
        
    }
    // employee team
    if ('team' in filters){
        var status =filters['team'];
        if(!isNaN(status)){
            $('#employee_team_selector').val(String(status));
        }
        
    }
    // filter ressource event 
    if ('showResEventRadio' in filters){
        var showResEventRadio =filters['showResEventRadio'];
        var selector = "#ressource_event_radio_box input[value='"+showResEventRadio+"']";
        $(selector).prop("checked", true);       
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
    $('#employee_team_selector').change(function() {   
        // save of filters values => see in js.labsmanager.filters.saveTableFilters
        saveTableFilters("calendar-filter", getCalenderFilters());
        calendar_refresh();
    });
    $('#ressource_event_radio_box').change(function(){
        selected_value = $("input[name='ressource_event_radio']:checked").val();
        saveTableFilters("calendar-filter", getCalenderFilters());
        calendar.setOption("filterResourcesWithEvents",selected_value!="false");
        calendar_refresh();
        
    });

}

function calendar_refresh(){
    //console.log("calendar_refresh")
    
    $('#calendar-box').unbind('click');
    calendar.refetchEvents();  
    calendar.refetchResources();  
}


