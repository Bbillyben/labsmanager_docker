// require main_calendar.js and its initialisation (for calendar var definition), those method only for manageing filters 

function getCalenderParams(){

    //////  DEV
    filters={type_exact:true,}// to not get descendant when selecting type
    $('#calendar-filter').find(".calendar-filter").each(function(){
        tmp={};
        // console.log("Params :"+$(this).prop('nodeName'))
        switch ($(this).prop('nodeName')) { 
            case 'SELECT':
            case "INPUT":// ensemble de check box
                tmp[$(this).data("filter-id")]=$(this).val();
                break;
            case "FORM":// radio box
                tmp[$(this).data("filter-id")]=$(this).find("input[type='radio']:checked").attr("value");
                break;
            case "DIV":// ensemble de check box
                tmp[$(this).data("filter-id")]= $.map($(this).find(':checkbox:checked'), function(n, i){
                                    return n.value;
                            }).join(',');
                break;
                
        }
        // console.log("tmp : "+JSON.stringify(tmp))
        filters= $.extend(filters, tmp); 

    })
    // console.log("getCalenderParams :"+JSON.stringify(filters))
    return filters
}
function initListener(){
    $('#calendar-filter').find(".calendar-filter").each(function(){
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
            saveTableFilters("calendar-filter", getCalenderParams());
            calendar_refresh();
        });

    })

    $('#ressource_event_radio_box').change(function(){// keep that one becaus he is specifique for calendar direct option
        selected_value = $("input[name='ressource_event_radio']:checked").val();
        saveTableFilters("calendar-filter", getCalenderParams());
        calendar.setOption("filterResourcesWithEvents",selected_value!="false");
        calendar_refresh();
        
    });

}
function Calendar_loadFilters(){
    // load filters values => see in js.labsmanager.filters.loadTableFilters
    var filters=loadTableFilters("calendar-filter");
    // console.log(" -------------------- Calendar_loadFilters")
    // console.log(JSON.stringify(filters))
    // console.log(" --------------------")
    for( slug in filters){
        elt = $('#calendar-filter').find(`.calendar-filter[data-filter-id="${slug}"]`)
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
function calendar_refresh(){
    //console.log("calendar_refresh")
    
    $('#calendar-box').unbind('click');
    calendar.refetchEvents();  
    calendar.refetchResources();  
}