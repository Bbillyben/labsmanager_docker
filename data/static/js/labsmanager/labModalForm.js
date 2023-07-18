$.fn.labModalForm = function(options) {
    var defaults = {
        modalID:"#create-modal",
        modalContent:".modal-content",
        modalForm:".modal-content form",
        isDeleteForm: false,
        addModalFormFunction:null,
        forceExitFunction: false,
        modal_title:null,
        asyncSettings:{
            directUpdate: true,
            closeOnSubmit: true,
            successMessage: "no mess",
            dataUrl: 'no url',
            dataElementId: 'no data elt',
            dataKey: 'table',
        }
    };
    settings = $.extend(defaults, options);

    if(!settings.formURL)throw new Error('[labModalForm] No formURL parameter !');

    $(this).modalForm({
        modalID: settings.modalID,
        modalContent: settings.modalContent,
        modalForm: settings.modalForm,
        formURL: settings.formURL,
        isDeleteForm: settings.isDeleteForm,
        errorClass: ".form-validation-warning",
        asyncUpdate: true,
        modal_title:settings.modal_title,
        asyncSettings: {
            directUpdate: settings.asyncSettings.directUpdate,
            closeOnSubmit: settings.asyncSettings.closeOnSubmit,
            successMessage: "no mess",
            dataUrl: 'no url',
            dataElementId: 'no data elt',
            dataKey: 'table',
            addModalFormFunction: settings.addModalFormFunction,
            forceExitFunction: settings.forceExitFunction,
        }
    });
}