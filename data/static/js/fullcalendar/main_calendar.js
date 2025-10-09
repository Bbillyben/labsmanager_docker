var user_id;
var calendar;
function initCalendar(userId){
    user_id=userId;
    
    Calendar_loadFilters("calendar-filter");
    initListener("calendar-filter");
    initFullCalendar();
}

function initFullCalendar(){

    var canMod=USER_PERMS.includes("leave.change_leave") || USER_PERMS.includes("is_staff");
    const calendarEl = document.getElementById('calendar-box')
    
    option={
        selectable:canMod,
        editable:canMod,
        extraParams:getCalenderParams('#calendar-filter'),
        filterResourcesWithEvents:$("#ressource_event_radio_box input[name='ressource_event_radio']:checked").val()!='false',
        cal_type:'main',
    }
    const view = localStorage.getItem(`labsmanager-calendar-view_main`);
    if (view){
        option.initialView = view
    }
    calendar = $('#calendar-box').lab_calendar_employee(option);
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
    if(options["type"]!='')option['extraParams']['type']=options["type"];
    if(options["emp_status"]!='')option['extraParams']['emp_status']=options["emp_status"];
    if(options["team"]!='')option['extraParams']['team']=options["team"];
    if(options["showResEventRadio"]!='')option['extraParams']['showResEventRadio']=options["showResEventRadio"];



    calendar = $('#calendar-box').lab_calendar_employee(option);
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
    var extraP = getCalenderParams('#calendar-filter')();
    options['type']=extraP.type;
    options['emp_status']=extraP.emp_status;
    options['team']=extraP.team;
    options["showResEventRadio"]=$("#ressource_event_radio_box input[name='ressource_event_radio']:checked").val();
    // console.log("Print Cal option :"+JSON.stringify(options));
    var csrftoken = getCookie('csrftoken');
    openWindowWithPost(printUrl, options, csrftoken)
}



// For Project Calendar
function initProjectFullCalendar(){
    Calendar_loadFilters("calendar-project-filter");
    initListener("calendar-project-filter");
    initProjectCalendar();

}

function initProjectCalendar(){

    option={
        selectable:false,
        editable:false,
        extraParams:getCalenderParams('#calendar-project-filter'),
        cal_type:'project',

        eventsources:[
                {
                    url:Urls['api:project-calendar-all-get-event'](),
                    method: 'GET',
                    extraParams:$.fn.lab_calendar.prototype.getExtraSetting,
                }
            ],
        resources:{
                    url: Urls['api:project-calendar-all-get-resources'](),
                    method: 'GET',
                    extraParams:$.fn.lab_calendar.prototype.getExtraSetting,
            },
        
    }
    cur_view = localStorage.getItem(`labsmanager-calendar-view_project`);
    if (cur_view){
        option.initialView = cur_view
    }
    calendar_project = $('#calendar-project-box').lab_calendar_project(option);

}