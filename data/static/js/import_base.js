


function init_import(){

    initFileSelectForm();
    var formData = {
        csrfmiddlewaretoken: getCookie('csrftoken')
    };
    $.ajax({
        type:"GET",
        url: Urls["import_funditem"](),
        data:formData,
        success: function( data )
        {
            // showMessage("Ok", {
            //     style: 'success',
            //     details: 'ajax call success',
            //     icon: 'fas fa-thick',
            // })
            $("#file_selection").html(data);
            // initFileSelectForm();
        },
        error:function( err )
        {
            showMessage("Error", {
                style: 'danger',
                details: 'ajax call error',
                icon: 'fas fa-cross',
            })
             $("#file_selection").html(err.responseText)
            console.log(JSON.stringify(err));
        },
    });

    // initFileSelectForm();

}

function initFileSelectForm(){
    // for extension guess format from guess_format of import export
    $('input.guess_format[type="file"]').change(function () {
        var files = this.files;
        var dropdowns = $(this.form).find('select.guess_format');
        if(files.length > 0) {
          var extension = files[0].name.split('.').pop().trim().toLowerCase();
          for(var i = 0; i < dropdowns.length; i++) {
            var dropdown = dropdowns[i];
            dropdown.selectedIndex = 0;
            for(var j = 0; j < dropdown.options.length; j++) {
              if(extension === dropdown.options[j].text.trim().toLowerCase()) {
                dropdown.selectedIndex = j;
                break;
              }
            }
          }
        }
      });

    // buton for template import 
    //ad it after selectot
    $("#btn_imp_cont").appendTo($("#id_resource").parent());
    $("#id_resource").parent().css("display", "flex");
    $("#get_import_template").click(function(e){downloadImportTemplate();})


    $("#file_select").submit(function (event) {
        event.preventDefault();
        var formData = new FormData(this);
        
        var object = {};
        formData.forEach(function(value, key){
            object[key] = value;
        });

        var csrftoken = getCookie('csrftoken');

        $.ajax({
            beforeSend: function(xhr) {
                xhr.setRequestHeader('X-CSRFToken', csrftoken);
            },
            type:"POST",
            url: Urls["import_funditem"](),
            data:formData,
            processData: false,
            contentType: false,
            success: function( data )
            {
                // showMessage("Fund Load Success", {
                //     style: 'success',
                //     details: 'ajax call success',
                //     icon: 'fas fa-thick',
                // })
                $("#file_selection").html(data);
                ini_confirm();

            },
            error:function( err )
            {
                showMessage("Fund Load Error", {
                    style: 'danger',
                    details: 'ajax call error',
                    icon: 'fas fa-cross',
                })
                $("#file_selection").html(err.responseText)
                console.log(JSON.stringify(err));
            },
        });


      });



}
function ini_confirm(){
    $("#back_to_select").click(function(){
        init_import();
    });

    $("#file_confirm").submit(function (event) {
        event.preventDefault();
        var formData = new FormData(this);
        
        var object = {};
        formData.forEach(function(value, key){
            object[key] = value;
        });
        
        var csrftoken = getCookie('csrftoken');

        $.ajax({
            beforeSend: function(xhr) {
                xhr.setRequestHeader('X-CSRFToken', csrftoken);
            },
            type:"POST",
            url: Urls["import_funditem_confirm"](),
            data:formData,
            processData: false,
            contentType: false,
            success: function( data )
            {
                showMessage("Import Success", {
                    style: 'success',
                    icon: 'fas fa-check',
                })
                $("#file_selection").html(data);
                ini_import_out();

            },
            error:function( err )
            {
                showMessage("Fund Load Error", {
                    style: 'danger',
                    details: 'ajax call error',
                    icon: 'fas fa-cross',
                })
                $("#import_table").html(err.responseText)
                console.log(JSON.stringify(err));
            },
        });


      });
}

function ini_import_out(){
    $("#import_back_select").click(function(){
        init_import();
    });
}
      



function downloadImportTemplate(e) {

    res_id=$("#id_resource").val();
    url = Urls["get_import_template"]()
    query_params = {resource:res_id}

    url += '?';

    constructFormBody({}, {
        title: $( "#id_resource option:selected" ).text()+' Template',
        fields: {
            format: {
                label: 'Format',
                help_text: 'Select File Format',
                required: true,
                type: 'choice',
                value: 'csv',
                choices: exportFormatOptions(),
            }
        },
        onSubmit: function(fields, form_options) {
            var format = getFormFieldValue('format', fields['format'], form_options);

            // Hide the modal
            $(form_options.modal).modal('hide');

            for (const [key, value] of Object.entries(query_params)) {
                url += `${key}=${value}&`;
            }

            url += `export=${format}`;

            location.href = url;
        }
    });
}