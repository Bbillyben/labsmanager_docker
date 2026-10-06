function print_calendar(filter_target, calendar_target, option={}){
    printUrl = Urls["calendar_project_print"]();
    calendarEl = document.getElementById(calendar_target);
    if (!calendarEl?.fullCalendarInstance) {
        console.error("NO fullCalendarInstance SAVED in DOM id="+calendar_target);
        return;
    }
    calendar = calendarEl.fullCalendarInstance;
    
    options = {};
    options['initialView']=calendar.view.type;
    var d = calendar.view.activeStart
    options['start']=d.toISOString();
    d = calendar.view.activeEnd
    options['end']=d.toISOString();

    var extraP = getCalenderParams('#'+filter_target)();
    options['extraParams']={};
    Object.assign(options, extraP);

    all_options = $.extend(options, option);

    console.log("Print Cal option :"+JSON.stringify(all_options));
    var csrftoken = getCookie('csrftoken');

    openWindowWithPost(printUrl, all_options, csrftoken)
}