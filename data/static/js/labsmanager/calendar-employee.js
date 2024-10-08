(function ($) {
    var elts;
    $.fn.lab_calendar_employee = function (options) {
        if(options.modal_target){
            elts = options.modal_target;
        }else{
            elts=$(this);
        }
        
        $.fn.lab_calendar.prototype.eventClicked = function (info){
            $(info.el).tooltip('dispose');
            $('.popover').popover('dispose');
            if (info.event.display == "background" )return  { html: "" }
            // console.log(JSON.stringify(info.event))
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
                titleP ='<div class="d-flex flex-wrap">'
                titleP += "<b>"+info.event.extendedProps.type+"</b>";
                titleP += '<span class="flex" style="flex-grow: 1;"></span>';
                titleP += '<div class="btn-group" role="group">';
                titleP += '<button type="button" id="popover_close" class="btn btn-close close" ></button>',
                titleP += '</div>';
                titleP += '</div>';
                textP = "<em><b>" + info.event.extendedProps.employee + "</b></em>";
                var d = new Date(info.event.end);
                if(d.getUTCHours()==0)d.setDate(d.getDate() - 1)
                textP += "</br>" + info.event.start.toLocaleDateString() + "<small> (" + info.event.extendedProps.start_period_di+")</small> " + " - " + d.toLocaleDateString() + "<small> (" + info.event.extendedProps.end_period_di+")</small>";
                if(info.event.extendedProps.comment) textP +="</br><i>"+ info.event.extendedProps.comment+"</i>";
                if(USER_PERMS.includes("leave.change_leave") || USER_PERMS.includes("leave.delete_leave") || USER_PERMS.includes("staff.view_employee")){
                    textP +="<hr/>";
                    textP +="<div class='d-flex flex-wrap btn-group btn-group-sm' role='group'>";
                    //textP +="<span class='btn-group'>";
                    if(USER_PERMS.includes("leave.change_leave"))textP +="<button class='icon edit_leave btn btn-success' data-form-url='/calendar/update/"+info.event.extendedProps.pk+"/' title='edit leave'><i type = 'button' class='fas fa-edit'></i></button>";
                    if(USER_PERMS.includes("staff.view_employee")) textP +="<a role='button' class=' btn btn-secondary' href='/staff/employee/"+info.event.extendedProps.employee_pk+"' title='navigate to user'><i type = 'button' class='fas fa-user'></i></a>"; 
                    if(USER_PERMS.includes("is_staff"))textP +="<a role='button' class=' btn btn-primary'  href='/admin/leave/leave/"+info.event.extendedProps.pk+"/change/' title='see in admin'><i type = 'button' class='fas fa-shield-halved'></i></a>"; 
                    //textP += '<span class="flex" style="flex-grow: 1;min-width:1.5em;"></span>';
                    if(USER_PERMS.includes("leave.delete_leave"))textP +="<button class='icon delete_leave btn btn-danger ' data-form-url='/calendar/delete/"+info.event.extendedProps.pk+"/' title='delete leave'><i type = 'button' class='fas fa-trash'></i></button>";
                    //textP +="</span>";

                    textP +="</div>";

                }

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
            updateLeaveButtonHandler();

        }


        function updateLeaveButtonHandler (){
            $("#popover_close").click(function(){$('.popover').popover('dispose');})
            $(".edit_leave").each(function () {
                $(this).labModalForm({
                    formURL:  $(this).data("form-url"),
                    addModalFormFunction: $.fn.lab_calendar.prototype.calendar_refresh,
                    modal_title:"Edit Leave",
                })
                $(this).click(function(){$('.popover').popover('dispose');})
            });
            $(".delete_leave").each(function () {
                
                $(this).labModalForm({
                    formURL:  $(this).data("form-url"),
                    isDeleteForm: true,
                    addModalFormFunction: $.fn.lab_calendar.prototype.calendar_refresh,
                    modal_title:"Delete Leave",
                })
                $(this).click(function(){$('.popover').popover('dispose');})
            });
        }

        // ---------------------- Selection de date  --------------------- //
        $.fn.lab_calendar.prototype.eventSelectHandler = function (info){
            // console.log("[eventSelectHandler] :"+JSON.stringify(info))
            $('.popover').popover('dispose');
            $(info.el).tooltip('dispose');

            var d = new Date(info.end);
            d.setDate(d.getDate() - 1)
            modURL=Urls['add_leave']()+"?start_date="+info.start.toISOString()+"&end_date="+d.toISOString();
            modURL+= $.fn.lab_calendar.prototype.getExtraSettingURL.call(this);
            resource=info.resource
            if(resource){
                modURL+="&employee="+resource.id
            }
            try{
                //$('#detail-panels').unbind('click');
                $(elts).modal('dispose');
            }catch (error) {
                console.log(error);
            }
            modURL = encodeURI(modURL);
            $(elts).labModalForm({
                formURL: modURL,
                addModalFormFunction: $.fn.lab_calendar.prototype.calendar_refresh,
                forceExitFunction: true,
                modal_title:"Leave",
                direct_show:true,
            })
            
        }

        // -------------------------  Update Event Functions --------------- //
        $.fn.lab_calendar.prototype.LeaveChangeHandler = function(evt){
            $('.popover').popover('dispose');
            $(evt.el).tooltip('dispose');
            datas=evt['event'];
            // console.log("LeaveChangeHandler called"+JSON.stringify(datas));
            ne={};
            ne["pk"]=datas["extendedProps"]["pk"];
            ne["employee"]=datas["extendedProps"]["employee_pk"];
            ne["type"]=datas["extendedProps"]["type_pk"];
            ds=datas["start"].toISOString().split('T');
            ne["start_date"]=ds[0];
            if(ds[1].substring(0, 2)== "12"){
                ne["start_period"]="MI"
            }else{
                ne["start_period"]="ST"
            }


            if(datas["end"]){
                de=datas["end"].toISOString().split('T');            
                if(de[1].substring(0, 2)== "12"){
                    ne["end_period"]="MI"
                    ne["end_date"]=de[0]
                }else{
                    d = new Date(de[0]);
                    d.setDate(d.getDate() - 1)
                    ne["end_date"]=d.toISOString().split('T')[0];
                    ne["end_period"]="EN"
                }
            }else{
                ne["end_date"]=ne["start_date"];
            }
            // console.log("new Event : "+JSON.stringify(ne));
            // ajax
            var csrftoken = getCookie('csrftoken');
            $.ajax({
                beforeSend: function(xhr) {
                    xhr.setRequestHeader('X-CSRFToken', csrftoken);
                },
                headers : {
                    'Accept' : 'application/json',
                    'Content-Type' : 'application/json'
                },
                url : Urls['api:leave-list']()+ne["pk"]+"/",
                type : 'PATCH',
                data : JSON.stringify(ne),
                success : function(response, textStatus, jqXhr) {
                    //console.log("Event Successfully Patched!");
                },
                error : function(jqXHR, textStatus, errorThrown) {
                    // log the error to the console
                    console.log("The following error occured: " + textStatus, errorThrown);
                },
                complete : function() {
                    calendar.refetchEvents();
                    callEventCallback(settingsCal);
                }
            });
        }

        $.fn.lab_calendar.prototype.eventContentRender =function (event, createElement){
            // console.log('[eventContentRender] called')
            // console.log(JSON.stringify(event))
            // console.log(event.view.type)
            htmlEvt = ""
            
            if (event.event.display == "background" && event.event.extendedProps.origin == "lm")return  { html: "" }


            if(event.view.type.toUpperCase().includes("YEAR")){
                start=event.event.start;
                end = event.event.end;
                if(!end)end = start   ;   
                if (end.getUTCHours() != 12 )end.setDate(end.getDate()-1);  
                const day1 = start.getDate();
                const month1 = start.getMonth()+1;
                const day2 = end.getDate();
                const month2 = end.getMonth()+1;

                dateField=day1 + (month1 != month2 ? "/" + month1:"") + ( day1 != day2 || month1 != month2 ? ' → ' + day2 + (month1 != month2 ? "/" + month2:""):"")
                htmlEvt = ' <span style="font-size:0.7em;font-weight:italic;">'+ dateField +' ⦿ </span>'+" "+htmlEvt;
            }



            props = event.event.extendedProps
            if(props.origin=="lm"){
                if(event.view.type.toUpperCase().includes("RESOURCE")){
                    htmlEvt += "<span class='resource-name'>"+props.type+"</span>" + '<span class="initial-circle"><span class="initial-circle-inner">'+ getInitials(props.employee).join('')+'</span></span>';
                    htmlEvt = "<div class='ressource-cont'>"+htmlEvt+"</div>"
                }else if(event.view.type.toUpperCase().includes("GRID")){
                    htmlEvt += props.employee + ' <small>-'+ props.type+'</small>';
                }else{
                    htmlEvt += props.employee + " - " + props.type;
                }
            }else if(event.event._def.title){
                htmlEvt += event.event._def.title;
            }else{
                htmlEvt += "<div style='min-height:1em;'></div>";
            }
            

            


            if (props.start_period_di == "Middle" ||  props.end_period_di== "Middle"){
                // console.log(event)
                htmlEvt = '<span style="width:50%;">'+htmlEvt+'</span>'
            }
            return  { html: htmlEvt }
        }

        
    //console.log("Modal Form Call :"+options.formURL);
        // Default settings
        var defaults = {
            // eventDrop: LeaveChangeHandler,
            // eventResize: LeaveChangeHandler,
            // eventClick: eventClicked,
            // select: eventSelectHandler,
            // eventContentRender:eventContentRender,
            eventsources:[
                {
                    url:Urls['api:leave-search-calendar'](),
                    method: 'GET',
                    extraParams:$.fn.lab_calendar.prototype.getExtraSetting,
                }
            ],
        };
        emplOptions = $.extend(defaults, options);
        calendar = $.fn.lab_calendar.call(this, emplOptions);
        return calendar;
    };


}(jQuery));