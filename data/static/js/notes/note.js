
(function ($) {
    var settings;
    var panel;
    var currentSel;
    const marker = "data-django-prose-editor"
    var currentEditor
    var saveTimeout
    var originalHash;
    var onSaveFlag = false;
    function update_notebtn_listener(){
        var addNew = $(panel).find('.add').first();
        
        addNew.unbind().labModalForm({
            formURL:  Urls['add_genericnote'](settings.app,settings.model,settings.pk),
            addModalFormFunction: load_note_data,
            modal_title:"Add Note",
            addModalPreFormFunction:stop_edit,
        });

        $(panel).find('.note-cont .edit').each(function(){
            $(this).on("click", function(){
                edit_note(this);
            })
            
        })
        $(panel).find('.note-cont .delete').each(function(){
            $(this).labModalForm({
                formURL:Urls['GenericNoteDeleteView']($(this).data("pk")),
                isDeleteForm: true,
                addModalFormFunction: load_note_data,
                modal_title:"Delete Note",
                addModalPreFormFunction:stop_edit,
            })
        })

        $(panel).find('.nav-notes').first().unbind().on('click', function(e){
            currentSel = $(this).find('.active').first().attr('id');
        })

        $(panel).find('.note-cont .edit-label').each(function(){
            $(this).labModalForm({
                formURL:Urls['GenericNoteUpdateView']($(this).data("pk")),
                addModalFormFunction: load_note_data,
                modal_title:"Update Note",
                addModalPreFormFunction:stop_edit,
            })
        })


        var tabEl = $(panel).find('.nav-link[data-bs-toggle="tab"]')
        tabEl.on('shown.bs.tab', function (event) {
            stop_edit();
        })


    }
    function createEditor(textarea) {
        
        if (textarea.closest(".prose-editor")) return
        const config = JSON.parse(textarea.getAttribute(marker))

        const {
            // Always recommended:
            Document, Dropcursor, Gapcursor, Paragraph, HardBreak, Text,

            // Add support for a few marks:
            Bold, Italic, Subscript, Superscript, Link,

            // A menu is always nice:
            Menu,
            createTextareaEditor,
        } = window.DjangoProseEditor

        const extensions = [
            Document, Dropcursor, Gapcursor, Paragraph, HardBreak, Text,

            Bold, Italic, Subscript, Superscript, 
        ]
        if (Link) {
            extensions.push(Link.configure({ openOnClick: false }));
          }
      
          if (Menu) {
            extensions.push(Menu.configure({ config }));
          }

        return DjangoProseEditor.createEditor(textarea, extensions)
    }
    function stop_edit(){
        if(currentEditor){
            checkForChange();
            var id = $(currentEditor).find(".dummytxtarea").data("id");            
            var editor =  $("#"+id+"-tab-pane").find(".prose-editor");
            var nText =editor.find(".ProseMirror").html();
            editor.remove();
            var disp_div = $("#"+id+"-tab-pane").find(".note-display")
            disp_div.show();
            disp_div.html(nText);
            $("#"+id+"-tab-pane").find(".note-footer .edit").prop('disabled', false);
            clearInterval(saveTimeout);
        }
        currentEditor = null;
    }
    function edit_note(target){
        var app = $(target).data("app");
        var model = $(target).data("model");
        var pk = $(target).data("pk");
        var id = $(target).data("id");
        var note_content=$("#"+id+"-tab-pane").find(".note-content")
        var note_div=note_content.find(".note-display")

        //  disable edit btn
        $("#"+id+"-tab-pane").find(".note-footer .edit").prop('disabled', true);
        // add the textarea
        var ta = '<textarea class="dummytxtarea proseeditorwidget" data-id="'+id+'" data-app="'+app+'" data-model="'+model+'"   data-pk="'+pk+'" data-django-prose-editor="{}">'+$(note_div).html()+'</textarea>'
        currentEditor = note_content.prepend(ta)
        
        const textareas = note_content.get(0).querySelector(`[${marker}]`);
         createEditor(textareas)
        note_div.hide();
        originalHash = hashText($(note_div).html())
        initiateFollowUp();
    }

    function initiateFollowUp(){
        saveTimeout = setInterval(checkForChange, 3000);
    }
    function checkForChange(){
        var nText = $(currentEditor).parent().find(".ProseMirror").html();
        if(hasHashChange(nText) && !onSaveFlag)saveCurrentNote();
    }
    function saveCurrentNote(){
        onSaveFlag=true;
        var pk = $(currentEditor).find(".dummytxtarea").data("pk");
        var id = $(currentEditor).find(".dummytxtarea").data("id");
        var note_text=$(currentEditor).find(".ProseMirror").html();
        data_note = JSON.stringify({
            note:note_text,
        });
        if (!pk){
            onSaveFlag=false;
            showMessage("Note loading", {
                            style: 'danger',
                            icon: 'fas fa-server icon-red',
                            details: "Error on save, note pk undefined",
                        });
                        return;
        }

        $("#"+id+"-tab-pane").find(".note-save .loader").show()
        $("#"+id+"-tab-pane").find(".note-save .text-success").hide()

        var csrftoken = getCookie('csrftoken');
        $.ajax({
            beforeSend: function(xhr) {
                xhr.setRequestHeader('X-CSRFToken', csrftoken);
            },
            headers : {
                'Accept' : 'application/json',
                'Content-Type' : 'application/json'
            },
            url : Urls['api:genericnote-detail'](pk),
            type : 'PATCH',
            data:data_note,
            success : function(response, textStatus, jqXhr) {
                var elH = $("#"+id+"-tab-pane").find(".note-save .text-success").show()
                setTimeout(() => {
                    elH.hide();
                }, 2000); 
            },
            error : function(jqXHR, textStatus, errorThrown) {
                // log the error to the console
                message = "The following error occured: " + textStatus+ '##' + errorThrown;
                showMessage("Note loading", {
                    style: 'danger',
                    icon: 'fas fa-server icon-red',
                    details: message,
                });
                
            },
            complete : function() {
                onSaveFlag=false;
                $("#"+id+"-tab-pane").find(".note-save .loader").hide()
            }
        });

    }
    function hashText(text) {
        let hash = 0;
        for (let i = 0; i < text.length; i++) {
            hash = (hash << 5) - hash + text.charCodeAt(i);
            hash |= 0; // Convertit en entier 32 bits
        }
        return hash;
    }
    // Fonction de vérification
    function hasHashChange(newText) {
        const newHash = hashText(newText);
        if (newHash !== originalHash) {
            originalHash = newHash; // Mettre à jour l'empreinte
            return true;
        } 
        return false;
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
            li += '<span class="nav-link " id="'+id+'" data-bs-toggle="tab" data-bs-target="#'+id+'-tab-pane" type="button" role="tab" aria-controls="{{idT}}-tab-pane" aria-selected="true">'+note.name;
            if(USER_PERMS.includes("infos.change_genericnote") || settings.custom_rule)li+="<sup><button class='icon edit-label btn' data-app='"+settings.app+"' data-model='"+settings.model+"' data-pk='"+note.pk+"' data-id='"+id+"'><i type = 'button' class='fas fa-pen-to-square'></i></button></sup>";
            li +='</span>';
            li += '</li>';
            $(li).insertBefore(liTarget);

            var date_opt={
                month:"short",
                hour: '2-digit',
                minute: '2-digit',
            };

            tab = '<div class="tab-pane fade show loaded" id="'+id+'-tab-pane" role="tabpanel" aria-labelledby="'+id+'-tab"  data-pk="'+note.object_id+'">';
            tab+='<div class="note-content " >';
            
            tab+='<div class="note-display">'+note.note+'</div>'
            tab+='</div>'

            tab +='<div class="note-footer">';
            tab+='<div class="note-date"><i class="fa-regular fa-calendar-plus"></i>'+format_date_iso(note.created_at, date_opt)+' - <i class="fa-solid fa-pen-to-square"></i>'+format_date_iso(note.updated_at, date_opt)+'</div>';
            tab+='<div class="note-save"><div class="loader" style="display:none;"></div><div class="text-success" style="display:none;">saved</div><div class="text-danger" style="display:none;">error</div></div>';
            tab+='<span class="flex" style="flex-grow: 1;"></span>';
            if(USER_PERMS.includes("is_staff"))tab+="<a  class='icon admin_btn btn btn-secondary' href='"+Urls["admin:infos_genericnote_change"](note.pk)+"'><i type = 'button' class='fas fa-shield-halved'></i></a>";
            if(USER_PERMS.includes("infos.change_genericnote") || settings.custom_rule)tab+="<button class='icon edit btn btn-success' data-app='"+settings.app+"' data-model='"+settings.model+"' data-pk='"+note.pk+"' data-id='"+id+"'><i type = 'button' class='fas fa-pen-to-square'></i></button>";
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