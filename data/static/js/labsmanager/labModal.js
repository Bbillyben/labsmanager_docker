(function ($) {

    var labModalSimple = function (settings) {
        console.log("THis is modal click")
        console.log(JSON.stringify(settings))

        url=settings.templateURL;
        
        if(settings.params && Object.keys(settings.params).length >0 )url+="?"+$.param(settings.params)
        

        $(settings.modalID).find(settings.modalContent).load(url, function () {
            $(settings.modalID).modal("show");
            if(settings.modal_title){
                $(settings.modalID+" #modal-title").html(settings.modal_title)
            }
        });
    };


    $.fn.labModal = function(options) {
        var defaults = {
            modalID:"#create-modal",
            modalContent:".modal-content",
            modalForm:".modal-content form",
        };
        var settings = $.extend(defaults, options);

        if(!settings.templateURL)throw new Error('[labModalForm] No Template URL parameter !');

        this.each(function () {
            $(this).unbind('click');
            // Add click event handler to the element with attached modalForm
            $(this).click(function (event) {
                // Instantiate new form in modal
                labModalSimple(settings);
            });
        });


    }
}(jQuery));
