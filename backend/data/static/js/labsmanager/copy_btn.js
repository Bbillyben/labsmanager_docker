(function ($) {

    var copytoclipboardnear = function (settings) {
        console.log("bt copy clic for :"+settings.target)
        switch (settings.target) {
            case 'siblings':
                copy_txt= $(settings.btn).siblings('.copy-target').text()
                break;
            case 'ancestors':
                copy_txt= $(settings.btn).closest('.copy-target').text()
                break;
            default:
                copy_txt= ""
          }
        console.log("text to copy : "+copy_txt)
        if (navigator.clipboard && window.isSecureContext) {
            navigator.clipboard.writeText(copy_txt);
            showMessage('Value Copied', {
                style: 'success',
                details: copy_txt + ' copied',
                icon: 'fas fa-check',
            });
        }else{
            var tempInput = $('<textarea>');
            $('body').append(tempInput);
            tempInput.val(copy_txt).select();
            try {
                // Copie dans le presse-papier
                document.execCommand('copy');
                showMessage('Value Copied', {
                    style: 'success',
                    details: copy_txt + ' copied',
                    icon: 'fas fa-check',
                });
            } catch (err) {
                showMessage('Error Copy', {
                    style: 'dager',
                    details: '"'+ copy_txt + '" NOT copied',
                    icon: 'fas fa-check',
                });
            }
            
            // Supprime l'élément temporaire
            tempInput.remove();
        }
        
    };


    $.fn.copy_btn = function(options={}) {
        // console.log("copy_btn call : "+this)
        var defaults = {
            target:"siblings",// could be "ancestors"
        };
        var settings = $.extend(defaults, options);
        settings.btn = this;

        this.each(function () {
            $(this).unbind('click');
            // Add click event handler to the element with attached modalForm
            $(this).click(function (event) {
                // Instantiate new form in modal
                copytoclipboardnear(settings);
            });
        });
    }
}(jQuery));