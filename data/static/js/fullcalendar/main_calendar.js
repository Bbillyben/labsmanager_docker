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