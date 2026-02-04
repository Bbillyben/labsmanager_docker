// require main_calendar.js and its initialisation (for calendar var definition), those method only for manageing filters 
// function getCalenderParams(){

function getCalenderParams(selector) {
    return function getCalendarParamsSelector() {
        // Initial filters object
        let filters = { type_exact: true }; // Prevent descendant types when selecting type

        // Loop through each filter element inside the provided selector
        $(selector).find(".calendar-filter").each(function() {
            let tmp = {}; // Temporary object to store filter data

            // Identify the element type (SELECT, INPUT, FORM, DIV)
            switch ($(this).prop('nodeName')) {
                case 'SELECT':
                case 'INPUT': // Input elements (e.g., checkboxes)
                    tmp[$(this).data("filter-id")] = $(this).val();
                    break;
                case 'FORM': // Radio button form
                    tmp[$(this).data("filter-id")] = $(this).find("input[type='radio']:checked").attr("value");
                    break;
                case 'DIV': // Checkbox group
                    tmp[$(this).data("filter-id")] = $.map($(this).find(':checkbox:checked'), function(n) {
                        return n.value;
                    }).join(',');
                    break;
            }

            // Merge the temporary filters with the main filters object
            filters = $.extend(filters, tmp);
        });

        // Return the final filters object
        return filters;
    };
}


function initListener(filter_target, calendar_target="calendar-box"){
    // filter_target : the id of filter container
    $('#'+filter_target).find(".calendar-filter").each(function(){
        switch ($(this).prop('nodeName')) { 
            case 'SELECT':
            case "FORM":// radio box
            case "INPUT":
                elt=$(this);
                break;
            case "DIV":// ensemble de check box
               elt=$(this).find(":checkbox")
                break;
        }

        elt.change(function() {  
            saveTableFilters(filter_target, getCalenderParams("#"+filter_target)());
            calendar_refresh(calendar_target);
        });

    })

    $('#ressource_event_radio_box').change(function(){// keep that one becaus he is specifique for calendar direct option
        selected_value = $("input[name='ressource_event_radio']:checked").val();
        saveTableFilters("calendar-filter", getCalenderParams());
        calendar.setOption("filterResourcesWithEvents",selected_value!="false");
        if(filter_target=="calendar-filter"){
            calendar_refresh();
        }else{
            calendar_project_refresh();
        }
        
    });

}
function Calendar_loadFilters(filter_target){
    // filter_target : the id of filter container
    var filters=loadTableFilters(filter_target);
    // console.log(" -------------------- Calendar_loadFilters")
    // console.log("filter_target :"+filter_target)
    // console.log(JSON.stringify(filters))
    // console.log(" --------------------")
    for( slug in filters){
        elt = $('#'+filter_target).find(`.calendar-filter[data-filter-id="${slug}"]`)
        dom=elt.prop('nodeName')
        switch (dom) { 
            case 'SELECT':
            case "INPUT":
                elt.val(String(filters[slug]));
                break;
            case "FORM":// radio box
                elt.find("input[value='"+filters[slug]+"']").prop("checked", true); 
                break;
            case "DIV":// ensemble de check box
                selected_values = filters[slug].split(",")
                elt.find(':checkbox').each(function(){
                    val = $(this).attr("value");
                    if(selected_values.includes(val)){
                        $(this).prop("checked", true)
                    }else{
                        $(this).prop("checked", false)
                    }
                })
                break;
        }
    }


}
// utils
function calendar_refresh(calendar_target){
    // console.log("calendar_refresh for", calendar_target)
    calendarEl = document.getElementById(calendar_target);
    if (calendarEl?.fullCalendarInstance) {
        $('#'+calendar_target).unbind('click');
        calendarEl.fullCalendarInstance.refetchEvents();
        calendarEl.fullCalendarInstance.refetchResources();
    }else{
        console.error("NO fullCalendarInstance SAVED in DOM id="+calendar_target);
    }
    
    // calendar.refetchEvents();  
    // calendar.refetchResources();  
}
function calendar_project_refresh(){
    //console.log("calendar_refresh")
    
    $('#calendar-project-box').unbind('click');
    calendar_project.refetchEvents();  
    calendar_project.refetchResources();  
}