(function ($) {

    function calendar_refresh(){
        //console.log("calendar_refresh")
        $('#calendar-box').unbind('click');
        calendar.refetchEvents(); 
        calendar.refetchResources();
        callEventCallback(settingsCal);
    }
    function callEventCallback(settings){
        if(undefined != settings.eventCallback)settings.eventCallback();
    }
    function getExtraSetting(){
        var extraSetting={};
        if(typeof settingsCal.extraParams === 'function'){
            extraSetting=settingsCal.extraParams();
        }else{
            extraSetting=settingsCal.extraParams
        }

        // to specify it's from calendar
        extraSetting["cal"]=1;
        return  extraSetting
    }
    function getExtraSettingURL(){
        extraSetting=getExtraSetting();
        extraSettingStr=""
        for (s in extraSetting) {
            extraSettingStr+="&"+s+"="+extraSetting[s]
        }
        return extraSettingStr;
    }

    // test if fund eligibility date include contract dates
    function testFundDate(fund, contract){
        fund_start =new Date(fund.start_date);
        fund_end =new Date(fund.end_date);
        start = new Date(contract.start);
        end = new Date(contract.end);
        end.setDate(end.getDate()-1);
        // console.log(fund_start+" - "+fund_end+" vs  "+start+" - "+end);
        return (start <= fund_end && start >= fund_start && end >= fund_start && end <= fund_end);
    }


    // **********************************   RENDERERs *************************** //
    // ************************************************************************** //

    function labelFormatter(renderInfo){
        // console.log(JSON.stringify(renderInfo))
        htmlRes=renderInfo.resource.extendedProps.user_name;
        if(USER_PERMS.includes("staff.view_employee")){
            htmlRes +=" <sup> <a href='"+Urls['employee'](renderInfo.resource._resource.id)+"' title='navigate to employee'><i type = 'button' class='fa-regular fa-circle-right d-print-none text-info'></i></a></sup>"; 
        }    
        
        var statStr = ""
        if(renderInfo.resource.extendedProps.status){
            for(var s in renderInfo.resource.extendedProps.status){
                statStr +=(statStr.length>0? ", ":"")+renderInfo.resource.extendedProps.status[s].type.shortname;
            }
        }
        htmlRes +="<p style='float:right;font-size:smaller;'><i>"+statStr+"</i></p>";
        return { html: htmlRes}
    }

    function eventContentRender(event, createElement){
        $('.popover').popover('dispose');
        // console.log('[eventContentRender] called')
        // console.log(JSON.stringify(event))
        // console.log(event.view.type)
        if(event.event.extendedProps.status ){
            return contract_event(event, createElement);
        }else {
            return draggingEvent(event, createElement);
        }
    }
    function draggingEvent(event, createElement){
        // console.log(JSON.stringify(event))
        props = event.event.extendedProps
        htmlEvt = "";
        htmlEvt += "<span class=''>";
        if(props.type)htmlEvt += props.type.short_name;
        htmlEvt += " / "+props.fund.project.name;
        htmlEvt += " # "+props.fund.funder.short_name;
        htmlEvt += " - "+props.fund.institution.short_name;
        htmlEvt += "</span>";
    
        start = event.event.start;
        end = new Date(start.getFullYear(), start.getMonth() + 1, 0);
        amount = props.fund.available_f - props.amount_left_effective - props.amount_left_prov
        // console.log("dragging amount :"+amount+"  ( amoun : "+props.fund.available_f+"  /  left eff :"+props.amount_left_effective+ " / prov :"+props.amount_left_prov+")")
        // wrapper to set effective contract or provisionnal as well as alert
        class_wrapper ="prospect ";
        if(!testFundDate(props.fund, {start:start, end:end})){
            class_wrapper+=" date-error";
        }else if(amount<=0){
            class_wrapper+=" avail-error";
        }



        htmlEvt = "<div class='ressource-cont-pros "+class_wrapper+"'>"+htmlEvt+"</div>"

        return  { html: htmlEvt };
    }
    function contract_event(event, createElement){
        htmlEvt = ""
        start=event.event.start
        end = event.event.end 
        if(event.view.type.toUpperCase().includes("YEAR")){
                    
            if (end.getUTCHours() != 12 )end.setDate(end.getDate()-1)
            const day1 = start.getDate();
            const month1 = start.getMonth()+1;
            const day2 = end.getDate();
            const month2 = end.getMonth()+1;

            dateField=day1 + (month1 != month2 ? "/" + month1:"") + ( day1 != day2 || month1 != month2 ? ' → ' + day2 + (month1 != month2 ? "/" + month2:""):"")
            htmlEvt = ' <span class="date-field" style="font-size:0.7em;font-weight:italic;">'+ dateField +' ⦿</span>'+" "+htmlEvt;
        }

        props = event.event.extendedProps
        htmlEvt += "<span class='resource-name'>";
       if(props.contract_type) htmlEvt += props.contract_type+" / ";
        htmlEvt += props.fund.project.name;
        htmlEvt += " # "+props.fund.funder.short_name;
        htmlEvt += " - "+props.fund.institution.short_name;
        htmlEvt += "</span>";
        if(props.remain_amount && props.total_amount){
            htmlEvt += "<span class='contract-info'>";
            htmlEvt += moneyDisplay(props.remain_amount)+" (<small>"+moneyDisplay(props.total_amount)+"</small>)";
            htmlEvt += "</span>";
        }
        
        // wrapper to set effective contract or provisionnal as well as alert
        class_wrapper ="contract "+props.status;
        //test date
        if(!testFundDate(props.fund, event.event)){
            class_wrapper+=" date-error";
        }
        htmlEvt = "<div class='ressource-cont-pros "+class_wrapper+"'>"+htmlEvt+"</div>"
        return  { html: htmlEvt }
    }

    

    // **********************************   EVENT Handlers *************************** //
    // ******************************************************************************* //
    // handle the event drop from external
    function dropHandler(infos){
        // console.log("[lab_contract_prov] Drop handler :");
        var droppedData = ($(infos.draggedEl).data("event"));
        // console.log(JSON.stringify(infos));
        // ajax call
        var csrftoken = getCookie('csrftoken');
        var data =  {};
        data["employee"]=infos.resource.id;
        data["fund"]=droppedData.fund.pk;
        data["start_date"]=infos.dateStr;
        var ed = new Date(infos.date.getFullYear(), infos.date.getMonth() + 1, 0);
        data["end_date"]=ed.toISOString().split('T')[0];
        data["is_active"]=false;
        $.ajax({
            beforeSend: function(xhr) {
                xhr.setRequestHeader('X-CSRFToken', csrftoken);
            },
            headers : {
                'Accept' : 'application/json',
                'Content-Type' : 'application/json'
            },
            url : Urls['api:contract-contract_add'](),
            type : 'POST',
            data : JSON.stringify(data),
            success : function(response, textStatus, jqXhr) {
                // console.log("ajax success : " + JSON.stringify(response), textStatus);
                // showMessage('Contract create success ', {
                //     style: 'success',
                //     icon: 'fas fa-user-times',
                // });
                calendar.refetchEvents();
            },
            error : function(jqXHR, textStatus, errorThrown) {
                // log the error to the console
                // console.log("The following error occured: " + textStatus, errorThrown);
                showMessage("The following error occured: " + textStatus, {
                    style: 'danger',
                    details: errorThrown,
                    icon: 'fas fa-user-times',
                });
            },
            complete : function(response) {
                // console.log("ajax complete : " + JSON.stringify(response));
                // calendar.refetchEvents();
            }
        });

    }

    function LeaveChangeHandler(evt){
        // console.log("[LeaveChangeHandler]");
        props = evt.event;
        var data =  {};
        var data =  {};
        data["pk"]=props.extendedProps.pk
        data["employee"]=evt.newResource?evt.newResource.id:props.extendedProps.employee;
        data["start_date"]=props.start.toISOString().split('T')[0];
        ed = props.end;
        ed.setDate(ed.getDate() - 1)
        data["end_date"]=ed.toISOString().split('T')[0];
        var csrftoken = getCookie('csrftoken');
        $.ajax({
            beforeSend: function(xhr) {
                xhr.setRequestHeader('X-CSRFToken', csrftoken);
            },
            headers : {
                'Accept' : 'application/json',
                'Content-Type' : 'application/json'
            },
            url : Urls['api:contract-contract_update'](),
            type : 'POST',
            data : JSON.stringify(data),
            success : function(response, textStatus, jqXhr) {
                // console.log("ajax success : " + JSON.stringify(response), textStatus);
                // showMessage('Contract create success ', {
                //     style: 'success',
                //     icon: 'fas fa-user-times',
                // });
                calendar.refetchEvents();
            },
            error : function(jqXHR, textStatus, errorThrown) {
                // log the error to the console
                // console.log("The following error occured: " + textStatus, errorThrown);
                showMessage("The following error occured: " + textStatus, {
                    style: 'danger',
                    details: errorThrown,
                    icon: 'fas fa-user-times',
                });
            },
            complete : function(response) {
                // console.log("ajax complete : " + JSON.stringify(response));
                // calendar.refetchEvents();
            }
        });

    }

    function eventClicked(info){
        $('.popover').popover('dispose');
        props = info.event.extendedProps;        
        titleP ='<div class="d-flex flex-wrap">'
        titleP += "<b>"+props.employee_username+"</b>";
        titleP += '<span class="flex" style="flex-grow: 1;"></span>';
        titleP += '<div class="btn-group" role="group">';
        titleP += '<button type="button" id="popover_close" class="btn btn-close close" ></button>',
        titleP += '</div>';
        titleP += '</div>';
        textP = "<em><b>" + props.fund.project.name + "</b></em></br>";
        textP += "<em><b>" + props.fund.funder.short_name+ " - "+props.fund.institution.short_name + "</b></em>";
        textP += "<sup><button class='show_contract_fund btn' data-form-url='"+Urls["api:contract-contract_fund_modal"](props.fund.pk)+"'><i class='fa-solid fa-circle-info'></i></button></sup> "
        var d = new Date(info.event.end);
        if(d.getUTCHours()==0)d.setDate(d.getDate() - 1)
        textP += "</br>" + info.event.start.toLocaleDateString() +  " - " + d.toLocaleDateString() ;
        // warnings
        if(!testFundDate(props.fund, info.event)){
            textP += "<div class=' alert-danger text-danger text-center'>"+"dates error";
            textP += "</br> fund :"+(new Date(props.fund.start_date)).toLocaleDateString()+" - "+(new Date(props.fund.end_date)).toLocaleDateString();
            
            textP += "</div>";
        }


        if(USER_PERMS.includes("expense.change_contract") || USER_PERMS.includes("expense.delete_contract") || USER_PERMS.includes("staff.view_employee")){
            textP +="<hr/>";
            textP +="<div class='d-flex flex-wrap btn-group btn-group-sm' role='group'>";
            //textP +="<span class='btn-group'>";
            if(props.status != "effe" && USER_PERMS.includes("expense.change_contract"))textP +="<button class='icon edit_contract btn btn-success' data-form-url='"+Urls["update_contract_open"](props.pk)+"' title='edit leave'><i type = 'button' class='fas fa-edit'></i></button>";
            if(USER_PERMS.includes("expense.add_contract_expense")) textP +="<button class='icon edit_contract btn btn-info' data-form-url='"+Urls["add_contract_expense"](props.pk)+"' style='color:#ffffff;' title='add contract expense'><i type = 'button' class='fas fa-solid fa-dollar-sign'></i></button>";
            if(USER_PERMS.includes("staff.view_employee")) textP +="<a role='button' class=' btn btn-secondary' href='/staff/employee/"+props.employee+"' title='navigate to user'><i type = 'button' class='fas fa-user'></i></a>";             
            if(USER_PERMS.includes("is_staff"))textP +="<a role='button' class=' btn btn-primary'  href='"+Urls["admin:expense_contract_change"](props.pk)+"' title='see in admin'><i type = 'button' class='fas fa-shield-halved'></i></a>"; 
           
            //textP += '<span class="flex" style="flex-grow: 1;min-width:1.5em;"></span>';
            if(props.status != "effe" && USER_PERMS.includes("expense.delete_contract"))textP +="<button class='icon delete_contract btn btn-danger ' data-form-url='"+Urls["delete_contract_open"](props.pk)+"' title='delete leave'><i type = 'button' class='fas fa-trash'></i></button>";
            //textP +="</span>";

            textP +="</div>";

        }

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
        updatePopOverButton();
    }
    function updatePopOverButton(){
        $("#popover_close").click(function(){$('.popover').popover('dispose');})
        $(".edit_contract").each(function () {
            $(this).labModalForm({
                formURL:  $(this).data("form-url"),
                addModalFormFunction: calendar_refresh,
                modal_title:"Edit Contract",
            })
            $(this).click(function(){$('.popover').popover('dispose');})
        });
        $(".delete_contract").each(function () {
            
            $(this).labModalForm({
                formURL:  $(this).data("form-url"),
                isDeleteForm: true,
                addModalFormFunction: calendar_refresh,
                modal_title:"Delete Contract",
            })
            $(this).click(function(){$('.popover').popover('dispose');})
        });
        $(".show_contract_fund").each(function () {
            // $(this).labModalForm({
            //     formURL:  $(this).data("form-url"),
            //     isDeleteForm: true,
            //     modal_title:"Infos",
            // })
            $(this).labModal({
                templateURL:  $(this).data("form-url"),
                modal_title:"Infos",
            })
            $(this).click(function(){$('.popover').popover('dispose');})
        });
    }


    // allow dragging only for non effective contract event
    function eventAllowHandler(dropLocation, draggedEvent){
        return draggedEvent.extendedProps.status!="effe"
    }
    $.fn.lab_contract_prov = function (options) {
        // console.log(" Create lab_contract_prov")
        // Default settings
        var language = window.navigator.userLanguage || window.navigator.language;
        var defaults = {
            selectable:true,
            editable: true, // Permet le glisser-déposer
            droppable: true, // Permet de recevoir des éléments glissés-déposés
            extraParams:{},
            eventDrop: LeaveChangeHandler,
            eventResize: LeaveChangeHandler,
            eventClick: eventClicked,
            // select: eventSelectHandler,
            drop: dropHandler,
            eventAllow: eventAllowHandler,
            // eventReceive: eventReceiveHandler,
            resourceLabelContent: labelFormatter, 
            local: language,
            height:"auto",
            filterResourcesWithEvents:false,
            initialView: 'resourceYearCustom',
            useDatePicker: true,
            headerToolbar: {
                left: 'prev,next today datePickerButton',
                center: 'title',
                right: 'resourceTimelineMonth,resourceBiMensualCustom resourceYearCustom,resource2YearsSlide,resource5YearsSlide'
            },
            cal_type:'default'
        };
        // Extend default settings with provided options
        settingsCal = $.extend(defaults, options);
        elts=this;

        var globals={
            schedulerLicenseKey: 'CC-Attribution-NonCommercial-NoDerivatives',
            timeZone: 'UTC',
            locale:settingsCal.local,
            initialView: settingsCal.initialView,
            headerToolbar:settingsCal.headerToolbar,
            resources:{
                url: Urls['api:employee-contract-resource'](),
                method: 'GET',
                extraParams:getExtraSetting,
            },
            resourceGroupField:"employee",
            resourceAreaWidth:"10%",
            selectable: settingsCal.selectable,
            editable: settingsCal.editable,
            // eventResize: settingsCal.eventResize,
            // eventClick: settingsCal.eventClick,
            select: settingsCal.select,
            height: settingsCal.height,
            resourceLabelContent:settingsCal.resourceLabelContent,
            resourceAreaWidth:"10%",
            eventSources:[{
                url: Urls['api:contract-contract_calendar'](),
                method: 'GET',
                extraParams:getExtraSetting,
            },
            ],
            eventContent:eventContentRender, 
            eventAllow: settingsCal.eventAllow,
            drop: settingsCal.drop,
            eventDrop: settingsCal.eventDrop,
            eventResize: settingsCal.eventResize,
            eventClick: settingsCal.eventClick,
            // eventReceive: settingsCal.eventReceive,
        }   

        // add date picker button
        if (settingsCal.useDatePicker == true){
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
            localStorage.setItem(`labsmanager-contract-view_`+settingsCal.cal_type, arg.view.type);
        }

        globals.views= { 
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
                    start.setMonth(0);
                    start.setDate(1);
                    const end = new Date(currentDate);
                    end.setMonth(11);
                    end.setDate(31);
                    return {
                        start: start.toISOString(),
                        end: end.toISOString()
                    };
                }
            }, 
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
                    month: 1
                  },
                slotLabelInterval: {
                    month: 1
                },
                slotLabelFormat: [
                    {
                        year: 'numeric',
                    },
                    {
                        month: 'short',
                    },
                ],
                visibleRange: function (currentDate) {
                    const start = new Date(currentDate);
                    start.setMonth(0);
                    start.setDate(1);
                    const end = new Date(currentDate);
                    end.setMonth(start.getMonth()+12);
                    end.setDate(31);
                    end.setFullYear(start.getFullYear()+4);
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
                    "weeks": 1
                },
                slotLabelFormat: [{
                    month: 'long',
                }, // top level of text
                {
                    week: 'numeric',
            
                }, // lower level of text
                ],
                visibleRange: function (currentDate) {
                    const start = new Date(currentDate);
                    start.setDate(1);
                    const end = new Date(currentDate);
                    end.setMonth(end.getMonth() + 2); // Ajoute 2 mois à la date de fin
                    end.setDate(-1);
                    return {
                        start: start.toISOString(),
                        end: end.toISOString()
                    };
                }
            }, 

        }
        eltCal=document.getElementById(this.attr('id'))
        calendar = new FullCalendar.Calendar(eltCal, globals)
        calendar.render();

        // console.log(calendar.adaptive)
        return calendar;

    };



}(jQuery));