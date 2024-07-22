
(function ($) {
    var settings;
    var panel;
    var currentSel;

    function update_notebtn_listener(){
        var addNew = $(panel).find('.add').first();
        
        addNew.unbind().labModalForm({
            formURL:  Urls['add_genericnote'](settings.app,settings.model,settings.pk),
            addModalFormFunction: load_note_data,
            modal_title:"Add Note",
        });

        $(panel).find('.note-cont .edit').each(function(){
            $(this).labModalForm({
                formURL:Urls['GenericNoteUpdateView']($(this).data("pk")),
                addModalFormFunction: load_note_data,
                modal_title:"Update Note",
            })
        })
        $(panel).find('.note-cont .delete').each(function(){
            $(this).labModalForm({
                formURL:Urls['GenericNoteDeleteView']($(this).data("pk")),
                isDeleteForm: true,
                addModalFormFunction: load_note_data,
                modal_title:"Delete Note",
            })
        })

        $(panel).find('.nav-notes').first().unbind().on('click', function(e){
            currentSel = $(this).find('.active').first().attr('id');
        })

    }
    function load_note_data(){

        // ajax call
        var csrftoken = getCookie('csrftoken');
        $.ajax({
            beforeSend: function(xhr) {
                xhr.setRequestHeader('X-CSRFToken', csrftoken);
            },
            headers : {
                'Accept' : 'application/json',
                'Content-Type' : 'application/json'
            },
            url : Urls['generic_info'](settings.app,settings.model,settings.pk),
            type : 'GET',
            success : function(response, textStatus, jqXhr) {
                populate_note_panel(response);
            },
            error : function(jqXHR, textStatus, errorThrown) {
                // log the error to the console
                message = "The following error occured: " + textStatus+ '##' + errorThrown;
                console.log(message);
                showMessage("Note loading", {
                    style: 'danger',
                    icon: 'fas fa-server icon-red',
                    details: message,
                });
            },
            complete : function() {
                
            }
        });
        
    }
    function add_note(note, liTarget, noteTarget){
        id = createIdFrom(note.name, note.pk);
            li = '<li class="nav-item loaded">';
            li += '<span class="nav-link " id="'+id+'" data-bs-toggle="tab" data-bs-target="#'+id+'-tab-pane" type="button" role="tab" aria-controls="{{idT}}-tab-pane" aria-selected="true">'+note.name+'</span>';
            li += '</li>';
            $(li).insertBefore(liTarget);

            var date_opt={
                month:"short",
                hour: '2-digit',
                minute: '2-digit',
            };

            tab = '<div class="tab-pane fade show loaded" id="'+id+'-tab-pane" role="tabpanel" aria-labelledby="'+id+'-tab"  data-pk="'+note.object_id+'">';
            tab+='<div class="note-content">'+note.note+'</div>'
            tab +='<div class="note-footer">';
            tab+='<div class="note-date"><i class="fa-regular fa-calendar-plus"></i>'+format_date_iso(note.created_at, date_opt)+' - <i class="fa-solid fa-pen-to-square"></i>'+format_date_iso(note.updated_at, date_opt)+'</div>';
            tab+='<span class="flex" style="flex-grow: 1;"></span>';
            if(USER_PERMS.includes("is_staff"))tab+="<a  class='icon admin_btn btn btn-secondary' href='"+Urls["admin:infos_genericnote_change"](note.pk)+"'><i type = 'button' class='fas fa-shield-halved'></i></a>";
            if(USER_PERMS.includes("infos.change_genericnote") || settings.custom_rule)tab+="<button class='icon edit btn btn-success' data-app='"+settings.app+"' data-model='"+settings.model+"' data-pk='"+note.pk+"'><i type = 'button' class='fas fa-pen-to-square'></i></button>";
            if(USER_PERMS.includes("infos.delete_genericnote"))tab+="<button class='icon delete btn btn-danger ' data-app='"+settings.app+"' data-model='"+settings.model+"' data-pk='"+note.pk+"'><i type = 'button' class='fas fa-trash'></i></button>";
            tab += '</div>';
            tab+= '</div>';
            noteTarget.append(tab);

    }
    function populate_note_panel(datas){
        // empty panel
        $(panel).find('.loaded').remove();
        // print datas
        var liTarget = $(panel).find('.nav-btn').first();
        var noteTarget = $(panel).find('.tab-content').first();
        datas.infos.forEach( (note, index)=>{
            add_note(note, liTarget, noteTarget)
        });
        set_selected_note();
        update_notebtn_listener();
    }
    function set_selected_note(){
        if(currentSel){
            target = $(panel).find("#"+currentSel);
            if(target.length){
                var targetPaneId = $(target).attr('data-bs-target');
                $(target).addClass('active');
                $(targetPaneId).addClass('show active');
                return;
            }else{
                currentSel = undefined;
            }
        }
        if(currentSel == undefined){
            var firstNavItem = $(panel).find(".nav-item.loaded .nav-link").first();
            var targetPaneId = firstNavItem.attr('data-bs-target');
            firstNavItem.addClass('active');
            $(targetPaneId).addClass('show active');

        }
    }
    $.fn.lab_note = function(options){
        var defaults = {
            custom_rule:false,
        }
        settings=$.extend(defaults, options);
        panel =this;
        load_note_data();
        update_notebtn_listener();
        
    }
}(jQuery));