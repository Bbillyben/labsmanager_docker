$.fn.labModalForm = function(options) {
    if(!$(this).length)return;
    var defaults = {
        modalID:"#create-modal",
        modalContent:".modal-body",
        modalForm:".modal-body form",
        isDeleteForm: false,
        addModalFormFunction:null,
        addModalPreFormFunction:null,
        forceExitFunction: false,
        modal_title:null,
        asyncSettings:{
            directUpdate: true,
            closeOnSubmit: true,
            successMessage: "no mess",
            dataUrl: 'no url',
            dataElementId: 'no data elt',
            dataKey: 'table',
        },
        direct_show:false,
    };
    settings = $.extend(defaults, options);

    if(!settings.formURL)console.error('[labModalForm] No formURL parameter !'+$(this));//throw new Error('[labModalForm] No formURL parameter !');

    $(this).modalForm({
        modalID: settings.modalID,
        modalContent: settings.modalContent,
        modalForm: settings.modalForm,
        formURL: settings.formURL,
        isDeleteForm: settings.isDeleteForm,
        errorClass: ".form-validation-warning",
        asyncUpdate: true,
        modal_title:settings.modal_title,
        direct_show:settings.direct_show,
        asyncSettings: {
            directUpdate: settings.asyncSettings.directUpdate,
            closeOnSubmit: settings.asyncSettings.closeOnSubmit,
            successMessage: "no mess",
            dataUrl: 'no url',
            dataElementId: 'no data elt',
            dataKey: 'table',
            addModalFormFunction: settings.addModalFormFunction,
            forceExitFunction: settings.forceExitFunction,
            addModalPreFormFunction: settings.addModalPreFormFunction,
        }
    });
}


