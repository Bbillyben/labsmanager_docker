(function ($) {
    var elts;
    $.fn.lab_calendar_project = function (options) {
        
        if(options.modal_target){
            elts = options.modal_target;
        }else{
            elts=$(this);
        }
        function truncateText(text, maxLength) {
            if (text.length <= maxLength) {
                return text;
            }
            return text.substring(0, maxLength) + '...';
        }
        function resourceRenderer(info){
            
            text = ""; //"<span>"+info.resource.extendedProps.group_type+"</span>"
            text += "<span class='resource "+info.resource.extendedProps.group_type+"'>";
            if (info.resource.extendedProps.url){
                text += '<a href="'+info.resource.extendedProps.url+'" >';
            }
            if(info.resource.extendedProps.group_type == "milestones"){
                text +='<span class="icon small '+(info.resource.extendedProps.is_milestone?"milestone":"task")+'" style="margin-right:0.5em">'+(info.resource.extendedProps.is_milestone?'<i class="fa-solid fa-thumbtack"></i>':'<i class="fa-solid fa-bars-progress"></i>')+'</span>';
                text += "<b>"+info.resource.title+"</b>";
                if(info.resource.extendedProps.desc)text += "<sup><span class='desc' title='"+truncateText(info.resource.extendedProps.desc, 50)+"'><i class='fa-solid fa-circle-info'></i></span></sup>";
                //return { html: text };
            }else if (info.resource.extendedProps.group_type == "project"){
                text += "<b>" + info.resource.title + "</b>";
            }else{
                text +=  info.resource.title ;
            }
            if (info.resource.extendedProps.url){
                text += '<\a>';
            }
            text += "</span>";
            return { html: text};
            
        }

        $.fn.lab_calendar.prototype.eventClicked = function (info){
            $('.popover').popover('dispose');
            // console.log(JSON.stringify(info.event.extendedProps))
            titleP = "";
            textP = "<div class='project_event'>"; 
            if (info.event.display == "background" )return  { html: "" }
            if(info.event.extendedProps.origin != "lm"){// if event from plugin
                    if(!info.event.title || !info.event.extendedProps.desc)return  { html: "" }// no title or no description provided
                    titleP = '<div class="d-flex flex-wrap">'
                    titleP += "<b>"+info.event.title+"</b>";
                    titleP += '<span class="flex" style="flex-grow: 1;"></span>';
                    titleP += '<div class="btn-group" role="group">';
                    titleP += '<button type="button" id="popover_close" class="btn btn-close close" ></button>',
                    titleP += '</div>';
                    titleP += '</div>';
                    textP =  info.event.extendedProps.desc;
                }else{ // if event labsmanager
                    switch(info.event.extendedProps.meta_type){
                        case 'milestone': 
                            titleP ='<div class="d-flex flex-wrap">'
                            titleP += "<b>"+info.event.extendedProps.name+"</b>";
                            titleP += '<span class="flex" style="flex-grow: 1;"></span>';
                            titleP += '<div class="btn-group" role="group">';
                            titleP += '<button type="button" id="popover_close" class="btn btn-close close" ></button>',
                            titleP += '</div>';
                            titleP += '</div>';
                            textP += '<div class="info d-flex flex-wrap"><span class="end_date">'+info.event.start.toLocaleDateString()+"</span>"
                            if(!info.event.extendedProps.is_milestone)textP += ' - <span class="end_date">'+info.event.end.toLocaleDateString()+"</span>"
                            textP += '<span class="flex median" style="flex-grow: 1;"></span>';
                            textP += '<span class="quotity">' + info.event.extendedProps.quotity*100 +"%</span></div>"
                            
                            textP += '<div class="desc">' + info.event.extendedProps.desc + '</div>'
                            
                            
                            if (info.event.extendedProps.employee.length>0){
                                
                                textP += '<hr class="solid">';
                                textP += "<ul>"
                                for(e of info.event.extendedProps.employee){
                                    // console.log(JSON.stringify(e))
                                    textP += "<li>"+e.user_name+"</li>"
                                }
                                textP += "</ul>"
                            }
                        
                            break;
                    }


                }
                textP += "</div>";

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

                $(info.el).popover('show');
                updateEvtButtonHandler();

        };
        function updateEvtButtonHandler (){
            $("#popover_close").click(function(){$('.popover').popover('dispose');})
        }
        $.fn.lab_calendar.prototype.eventSelectHandler = function (info){
            console.log("lab_calendar_project - eventSelectHandler : to be implemented")
        };
        $.fn.lab_calendar.prototype.LeaveChangeHandler = function(evt){
        console.log("lab_calendar_project - LeaveChangeHandler : to be implemented")
        };
        $.fn.lab_calendar.prototype.eventContentRender =function (event, createElement){ 
            htmlEvt = "";
            props = event.event.extendedProps
            
            if(props.meta_type =='milestone'){
                if(props.overdue==true){
                    ms_status="overdue";
                }else if(props.status == true){
                    ms_status="done";
                }else{
                    ms_status="ongoing";
                }
                htmlEvt += "<span class='project_ms_cal status_" + ms_status +"' >"
                htmlEvt +=  "<span class='cal_label_resource' >"
                htmlEvt += props.name;
                htmlEvt += "</span>";
                if(props.employee.length == 1)htmlEvt += '<i class="samll fa-solid fa-user" style="margin-left:0.3em;"></i>';
                if(props.employee.length > 1)htmlEvt += '<i class="samll fa-solid fa-users" style="margin-left:0.3em;"></i>';
                const percentage = Math.round(props.quotity * 100);
                htmlEvt += `
                    <div class="completion_bar_container">
                        <div class="completion_bar_fill" style="width: ${percentage}%;"></div>
                    </div>
                `;
                
                htmlEvt += "</span>";
            }else if(props.meta_type =='participant'){
                htmlEvt += "<span class='project_part_cal status_" + props.status + "' >";
                htmlEvt +=  "<span class='cal_label_resource' >"
                htmlEvt += props.name
                if(props.quotity>0)htmlEvt +=" - <i class='small'>"+props.quotity *100 +"%</i>";
                htmlEvt += "</span>";
                htmlEvt += "</span>";
            }else if(props.meta_type =='project'){
                htmlEvt += "<span class='project_cal' ><span class='cal_label_resource' >"
                htmlEvt += props.name;
                htmlEvt += "</span></span>";
            }else if(props.meta_type =='fund'){
                htmlEvt += "<span class='project_fund_cal' ><span class='cal_label_resource' >"
                htmlEvt += props.name;
                htmlEvt += "</span></span>";
            }else{
                    htmlEvt += "<div style='min-height:1em;'></div>";
                }

            return  { html: htmlEvt }

        };
        var defaults = {
            datesSet: function(info) {/// to update resoures on time frame change
                info.view.calendar.refetchResources();
                },
            resourceGroupField:"group",
            resourceOrder: 'group,group_order',
            resources:{
                    url: Urls['api:project-calendar-get-resources'](options.extraParams.project),
                    method: 'GET',
                    extraParams:$.fn.lab_calendar.prototype.getExtraSetting,
                },

            eventsources:[
                {
                    url:Urls['api:project-calendar-get-event'](options.extraParams.project),
                    method: 'GET',
                    extraParams:$.fn.lab_calendar.prototype.getExtraSetting,
                }
            ],
            resourceLabelContent:resourceRenderer,
            headerToolbar: {
                    left: 'prev,next today datePickerButton',
                    center: 'title',
                    right: 'resourceTimelineMonth,resourceBiMensualCustom,resourceYearCustom,resource2YearsSlide,resource5YearsSlide,resource10YearsSlide'
            },

            views:{ 
                resource2YearsSlide: {
                    type: 'resourceTimeline',
                    buttonText: '2 Years',
                    dateIncrement: { month: 3 },
                    slotDuration: {
                        "month": 1
                    },
                    slotLabelInterval: {
                        "month": 1
                    },
                    slotLabelFormat: [
                        {
                            year: 'numeric',
                        },
                        {
                        month: 'short',
                    }, // top level of text
                    ],
                    visibleRange: function (currentDate) {
                        const start = new Date(currentDate);
                        //start.setMonth(0);
                        start.setDate(1);
                        const end = new Date(currentDate);
                        end.setMonth(start.getMonth()+12);
                        end.setDate(31);
                        end.setFullYear(start.getFullYear()+2);
                        return {
                            start: start.toISOString(),
                            end: end.toISOString()
                        };
                    }
                }, 
                resource5YearsSlide:
                {
                    type: 'resourceTimeline',
                    buttonText: '5 Years',
                    dateIncrement: { year: 1 },
                    slotDuration: {
                        month: 3
                    },
                    slotLabelInterval: {
                        month: 3
                    },
                    slotLabelFormat: [
                        {
                            year: 'numeric',
                        },
                        function(arg) {
                            const date = new Date(arg.date.marker);
                            const month = date.getMonth();
                            const quarter = Math.floor(month / 3) + 1;
                            return 'T' + quarter;
                                
                        }
                    ],
                    visibleRange: function (currentDate) {
                        const start = new Date(currentDate);
                        start.setMonth(0);
                        start.setDate(1);
                        const end = new Date(currentDate);
                        end.setFullYear(start.getFullYear() + 4);
                        end.setMonth(11); // Décembre
                        end.setDate(31);
                        return {
                            start: start.toISOString(),
                            end: end.toISOString()
                        };
                    }
                },  
                resource10YearsSlide:
                {
                    type: 'resourceTimeline',
                    buttonText: '10 Years',
                    dateIncrement: { year: 1 },
                    slotDuration: {
                        month: 3
                    },
                    slotLabelInterval: {
                        month: 3
                    },
                    slotLabelFormat: [
                        {
                            year: 'numeric',
                        },
                        function(arg) {
                            const date = new Date(arg.date.marker);
                            const month = date.getMonth();
                            const quarter = Math.floor(month / 3) + 1;
                            return 'T' + quarter;
                                
                        }
                    ],
                    visibleRange: function (currentDate) {
                        const start = new Date(currentDate);
                        start.setMonth(0);
                        start.setDate(1);
                        const end = new Date(currentDate);
                        end.setFullYear(start.getFullYear() + 9);
                        end.setMonth(11); // Décembre
                        end.setDate(31);
                        return {
                            start: start.toISOString(),
                            end: end.toISOString()
                        };
                    }
                },  

            }
        };
        emplOptions = $.extend(defaults, options);
        calendar = $.fn.lab_calendar.call(this, emplOptions);
        return calendar;
    };
        
}(jQuery));