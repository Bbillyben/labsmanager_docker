(function ($) {
   
    $.fn.lab_calendar = function (options) {
        //console.log("Modal Form Call :"+options.formURL);
            // Default settings
            plugin = $.fn.lab_calendar.prototype;
            var language = window.navigator.userLanguage || window.navigator.language;
            //console.log(language.split("-")[0])
            var defaults = {
                datesSet:'',
                selectable:false,
                editable:false,
                extraParams:{},
                eventDrop: plugin.LeaveChangeHandler,
                eventResize: plugin.LeaveChangeHandler,
                eventClick: plugin.eventClicked,
                select: plugin.eventSelectHandler,
                local: language,
                height:"auto",
                filterResourcesWithEvents:false,
                initialView: 'resourceTimelineMonth',
                useDatePicker: true,
                resourceOrder:'title',
                headerToolbar: {
                    left: 'prev,next today datePickerButton',
                    center: 'title',
                    right: 'resourceTimelineMonth,resourceBiMensualCustom,resourceYearCustom,resourcefortnightCustom dayGridMonth,dayGridWeek,listWeek,timelineYearCustom resourceMensualWeekSlide'
                },
                cal_type:'default', 
                eventsources:[]
            };

            // Extend default settings with provided options
            plugin.settingsCal = $.extend(defaults, options);
            elts=this;


            // source event construction ----------------------------
            eventSourceConstruct=[]
            plugin.settingsCal.eventsources.forEach(item => {
                eventSourceConstruct.push(item);                
            });
            // add plugin event            
            eventSourceConstruct.push({ 
                url: Urls['api-plugin-calendarevent'](),
                method: 'POST',
                extraParams:plugin.getExtraSetting_plugin,
            })
            var globals={
                datesSet: plugin.settingsCal.datesSet,
                schedulerLicenseKey: 'CC-Attribution-NonCommercial-NoDerivatives',
                
                timeZone: 'UTC',
                locale:plugin.settingsCal.local,
                initialView: plugin.settingsCal.initialView,
                headerToolbar:plugin.settingsCal.headerToolbar,
                // resources:{
                //     url: Urls['api:employee-calendar-resource'](),
                //     method: 'GET',
                //     extraParams:plugin.getExtraSetting,
                // },
                eventSources:eventSourceConstruct,
                
                
                resourceAreaWidth:"10%",
                selectable: plugin.settingsCal.selectable,
                editable: plugin.settingsCal.editable,
                eventDrop: plugin.settingsCal.eventDrop,
                eventResize: plugin.settingsCal.eventResize,
                eventClick: plugin.settingsCal.eventClick,
                select: plugin.settingsCal.select,
                height: plugin.settingsCal.height,
                
                resourceOrder: plugin.settingsCal.resourceOrder,
                filterResourcesWithEvents:plugin.settingsCal.filterResourcesWithEvents,
                // -------------------------------
                slotDuration: {
                    "hours": 12
                  },
                slotLabelInterval: {
                "hours": 24
                },
                slotLabelFormat: [{
                    month: 'long',
                    week: "short",
                }, // top level of text
                {
                    weekday: 'short',
                    day: 'numeric'
            
                } // lower level of text
                ],

                  // ------------------------------------------
                
                  eventContent:plugin.eventContentRender,  
                  eventDisplay:'block',
            }

            // console.log("####################### event sources ###################### ")
            // console.log(JSON.stringify(globals.eventSources))
            // console.log("############################################# ")
            //******** resources settings ******* */
            if(plugin.settingsCal.resources){
                globals.resources=plugin.settingsCal.resources;
            }else{
                globals.resources={
                    url: Urls['api:employee-calendar-resource'](),
                    method: 'GET',
                    extraParams:plugin.getExtraSetting,
                };
            }

            if(plugin.settingsCal.resourceLabelContent){
                globals.resourceLabelContent = plugin.settingsCal.resourceLabelContent
            }else{
                globals.resourceLabelContent = function(renderInfo) {
                    htmlRes=renderInfo.fieldValue
                    return { html: htmlRes}
                };
            }
            globals.resourceGroupField = plugin.settingsCal.resourceGroupField?plugin.settingsCal.resourceGroupField:"";
            

            /******  use of date picker */
            if (plugin.settingsCal.useDatePicker == true){
                globals.customButtons={
                    datePickerButton: {
                        text:'select',
                        click: function () {      
                            var $btnCustom = $('.fc-datePickerButton-button'); // name of custom  button in the generated code
                            $btnCustom.after('<input type="hidden" id="hiddenDate" class="datepicker"/>');
        
                            $("#hiddenDate").datepicker({
                                showOn: "button",
        
                                dateFormat:"yy-mm-dd",
                                onSelect: function (dateText, inst) {
                                    //$(this).fullCalendar('gotoDate', dateText);
                                    calendar.gotoDate(dateText);
                                },
                                beforeShow: function() {
                                    setTimeout(function(){
                                        $('.ui-datepicker').css('z-index', 99999999999999);
                                    }, 0);
                                },
                            });
        
                            var $btnDatepicker = $(".ui-datepicker-trigger"); // name of the generated datepicker UI 
                            //Below are required for manipulating dynamically created datepicker on custom button click
                            $("#hiddenDate").show().focus().hide();
                            $btnDatepicker.trigger("click"); //dynamically generated button for datepicker when clicked on input textbox
                            $btnDatepicker.hide();
                            $btnDatepicker.remove();
                            $("input.datepicker").not(":first").remove();//dynamically appended every time on custom button click
        
                        }
                    },
                }
            }

            // add pref save
            globals.viewClassNames =function(arg){
                localStorage.setItem(`labsmanager-calendar-view_`+plugin.settingsCal.cal_type, arg.view.type);
            }

            // add customs views
            /* TODO : only add necessary views */
            
            globals.views= {
                timelineYearCustom: {
                    type: 'timeline',
                    buttonText: 'Year',
                    dateIncrement: { years: 1 },
                    slotDuration: { months: 1 },
                    slotLabelInterval: {
                        "month": 1
                        },
                        slotLabelFormat: [{
                            month: 'long',
                            week: "short",
                        }, // top level of text
                        ],
                    visibleRange: function (currentDate) {
                        const start = new Date(currentDate);
                        start.setMonth(0, 1); // 1er janvier

                        const end = new Date(start);
                        end.setFullYear(start.getFullYear() + 1); // 1er janvier année suivante

                        return {
                            start: start.toISOString(),
                            end: end.toISOString()
                        };
                    },

                }, 
                resourceYearCustom: {
                    type: 'resourceTimeline',
                    buttonText: 'Year',
                    dateIncrement: { years: 1 },
                    slotDuration: { months: 1 },
                    slotLabelInterval: {
                        "month": 1
                        },
                        slotLabelFormat: [{
                            month: 'long',
                            week: "short",
                        }, // top level of text
                        ],
                    visibleRange: function (currentDate) {
                        const start = new Date(currentDate);
                        start.setMonth(0, 1); // 1er janvier

                        const end = new Date(start);
                        end.setFullYear(start.getFullYear() + 1); // 1er janvier année suivante

                        return {
                            start: start.toISOString(),
                            end: end.toISOString()
                        };
                    },
                }, 
                resourcefortnightCustom: {
                    type: 'resourceTimeline',
                    buttonText: 'fortnight',
                    dateIncrement: { weeks: 1 },
                    slotLabelFormat: [{
                        month: 'long',
                    }, // top level of text
                    {
                        weekday: 'short',
                        day: 'numeric',
                
                    }, // lower level of text
                    ],
                    slotDuration: {
                            "hours": 12
                          },
                    slotLabelInterval: {
                        "hours": 24
                        },
                    visibleRange: function (currentDate) {
                        const d = new Date(currentDate);

                        // monday current week
                        const monday = new Date(d);
                        const day = (d.getDay() + 6) % 7; // note lundi = 0
                        monday.setDate(d.getDate() - day);

                        const startYear = monday.getFullYear();
                        const startMonth = monday.getMonth() + 1;
                        const startDay = monday.getDate();

                        // end = monday + 14 days (exclus)
                        const end = new Date(monday);
                        end.setDate(monday.getDate() + 14);

                        const endYear = end.getFullYear();
                        const endMonth = end.getMonth() + 1;
                        const endDay = end.getDate();

                        return {
                            start: `${startYear}-${String(startMonth).padStart(2, '0')}-${String(startDay).padStart(2, '0')}`,
                            end: `${endYear}-${String(endMonth).padStart(2, '0')}-${String(endDay).padStart(2, '0')}`
                        };
                    }

                }, 
                resourceMensualWeekSlide: {
                    type: 'resourceTimeline',
                    buttonText: 'Month',
                    dateIncrement: { weeks: 1 },
                    slotDuration: {
                        "hours": 12
                      },
                    slotLabelInterval: {
                        "hours": 24
                    },
                    slotLabelFormat: [{
                        month: 'long',
                    }, // top level of text
                    {
                        weekday: 'short',
                        day: 'numeric',
                
                    }, // lower level of text
                    ],
                    visibleRange: function (currentDate) {
                        const start = new Date(currentDate);
                        start.setDate(start.getDate() - (start.getDay() + 6) % 7); // previous monday
                        const end = new Date(start);
                        end.setDate(start.getDate()+31);
                        end.setDate(end.getDate() - (end.getDay() + 6) % 7);
                        return {
                            start: start.toISOString(),
                            end: end.toISOString()
                        };
                    }
                }, 
                resourceBiMensualCustom: {
                    type: 'resourceTimeline',
                    buttonText: 'Bi Mensual',
                    dateIncrement: { months: 1 },
                    slotDuration: { days: 1 },
                    slotLabelInterval: {
                        "days": 1
                    },
                    slotLabelFormat: [{
                        month: 'long',
                    }, // top level of text
                    {
                        day:'numeric',
                
                    }, // lower level of text
                    ],
                    visibleRange: function (currentDate) {
                            const year = currentDate.getFullYear();
                            const month = currentDate.getMonth(); // 0-based

                            const start = `${year}-${String(month + 1).padStart(2, '0')}-01`;

                            const endMonth = month + 2;
                            const endYear = year + Math.floor(endMonth / 12);
                            const endMonthNorm = (endMonth % 12) + 1;

                            const end = `${endYear}-${String(endMonthNorm).padStart(2, '0')}-01`;

                            return { start, end };
                        }

                }, 

            }
            if(plugin.settingsCal.views){
                globals.views = $.extend(globals.views, plugin.settingsCal.views);
            }

            const eltCal=document.getElementById(this.attr('id'))
            calendar = new FullCalendar.Calendar(eltCal, globals)
            calendar.render();
            plugin.calendar_refresh(this.attr('id'));
            eltCal.fullCalendarInstance = calendar;
            return calendar;
    };
    
    var plugin = $.fn.lab_calendar.prototype;
    plugin.settingsCal={};
    plugin.calendar_refresh = function(id="calendar-box"){
        //console.log("calendar_refresh")
        $('#'+id).unbind('click');
        calendar.refetchEvents(); 
        calendar.refetchResources();
        plugin.callEventCallback(plugin.settingsCal);
    }

    plugin.eventClicked = function (info){
        console.error("Lab Calendar Implementation Error : eventClicked should be overriden")

    }


    plugin.updateLeaveButtonHandler = function(){
        $("#popover_close").click(function(){$('.popover').popover('dispose');})
        $(".edit_leave").each(function () {
            $(this).labModalForm({
                formURL:  $(this).data("form-url"),
                addModalFormFunction: calendar_refresh,
                modal_title:"Edit Leave",
            })
            $(this).click(function(){$('.popover').popover('dispose');})
        });
        $(".delete_leave").each(function () {
            
            $(this).labModalForm({
                formURL:  $(this).data("form-url"),
                isDeleteForm: true,
                addModalFormFunction: calendar_refresh,
                modal_title:"Delete Leave",
            })
            $(this).click(function(){$('.popover').popover('dispose');})
        });
    }

    plugin.getExtraSetting = function(){
        var extraSetting={};
        
        if(typeof plugin.settingsCal.extraParams === 'function'){
            extraSetting=plugin.settingsCal.extraParams();
        }else{
            extraSetting = $.extend(extraSetting, plugin.settingsCal.extraParams);
        }

        // to specify it's from calendar
        extraSetting["cal"]=1;

        if(typeof calendar !== 'undefined') {
            var view = calendar.view;
            extraSetting["start"] = view.activeStart.toISOString();
            extraSetting["end"] = view.activeEnd.toISOString();
        } else {
            // Valeurs par défaut pour l'initialisation
            extraSetting["start"] = new Date().toISOString();
            extraSetting["end"] = new Date(new Date().setDate(new Date().getDate() + 30)).toISOString();
        }
        
        
        // extra params for 
        return  extraSetting
    }
    plugin.getExtraSetting_plugin = function(){
        extraSetting = plugin.getExtraSetting();
        var csrftoken = getCookie('csrftoken');
        extraSetting["csrfmiddlewaretoken"] = csrftoken
        if(typeof(calendar) == 'undefined'){
            extraSetting["view"]=plugin.settingsCal.initialView;
            extraSetting['resources']=null;
        }else{
            extraSetting["view"]=calendar.view.type;
            extraSetting['resources']=JSON.stringify(calendar.getResources());
        }
        extraSetting['settings']=JSON.stringify(plugin.settingsCal);
        return  extraSetting
    }
    plugin.getExtraSettingURL = function(){
        
        extraSetting=plugin.getExtraSetting();
        extraSettingStr=""
        for (s in extraSetting) {
            extraSettingStr+="&"+s+"="+extraSetting[s]
        }

        return extraSettingStr;
    }
    // ---------------------- Selection de date  --------------------- //
    plugin.eventSelectHandler = function(info){
        console.error("Lab Calendar Implementation Error : 'eventSelectHandler' should be overriden")
    }

    // -------------------------  Update Event Functions --------------- //
    plugin.LeaveChangeHandler = function(evt){
        console.error("Lab Calendar Implementation Error : 'LeaveChangeHandler' should be overriden")
    }

    plugin.callEventCallback = function(settings){
        if(undefined != settings.eventCallback)settings.eventCallback();
    }
    plugin.eventContentRender = function(event, createElement){
        console.error("Lab Calendar Implementation Error : 'eventContentRender' should be overriden")
    }


}(jQuery));