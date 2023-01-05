function initSettingsPage(){


    $('table').find('.boolean-setting').change(function() {

        var pk = $(this).attr('pk');
        var setting = $(this).attr('setting');
        var plugin = $(this).attr('plugin');
        var user = $(this).attr('user');
        var notification = $(this).attr('notification');

        var checked = this.checked;

        // Global setting by default
        var url = `/api/settings/global/${setting}/`;

        if  (user) {
            url = `/api/settings/user/${setting}/`;
        }

        labsmanagerPut(
            url,
            {
                value: checked.toString(),
            },
            {
                method: 'PATCH',
                success: function(data) {
                },
                error: function(xhr) {
                    showApiError(xhr, url);
                }
            }
        );

    });

    // Callback for when non-boolean settings are edited
    $('table').find('.btn-edit-setting').click(function() {
        var setting = $(this).attr('setting');
        var plugin = $(this).attr('plugin');
        var is_global = true;
        var notification = $(this).attr('notification');

        if ($(this).attr('user')){
            is_global = false;
        }

        var title = '';

        if (plugin != null) {
            title = 'Edit Plugin Setting';
        } else if (notification) {
            title = 'Edit Notification Setting';
            setting = $(this).attr('pk');
        } else if (is_global) {
            title = 'Edit Global Setting';
        } else {
            title = 'Edit User Setting';
        }

        editSetting(setting, {
            plugin: plugin,
            global: is_global,
            notification: notification,
            title: title,
        });
    });

    $("#edit-user").on('click', function() {
        launchModalForm(
            "{% url 'edit-user' %}",
            {
                reload: true,
            }
        );
    });

    $("#edit-password").on('click', function() {
        launchModalForm(
            "{% url 'set-password' %}",
            {
                reload: true,
            }
        );
    });


}



/*
 * Interactively edit a setting value.
 * Launches a modal dialog form to adjut the value of the setting.
 */
function editSetting(key, options={}) {


    var  url = `/api/settings/user/${key}/`;


    // First, read the settings object from the server
    labsmanagerGet(url, {}, {
        success: function(response) {
            reload_required = true;
            if (response.choices && response.choices.length > 0) {
                response.type = 'choice';
                reload_required = true;
            }

            // Construct the field
            var fields = {
                value: {
                    label: response.name,
                    help_text: response.description,
                    type: response.type,
                    choices: response.choices,
                    value: response.value,
                }
            };
            console.log("editSetting - "+JSON.stringify(fields));

            // Foreign key lookup available!
            if (response.type == 'related field') {

                if (response.model_name && response.api_url) {
                    fields.value.type = 'related field';
                    fields.value.model = response.model_name.split('.').at(-1);
                    fields.value.api_url = response.api_url;
                } else {
                    // Unknown / unsupported model type, default to 'text' field
                    fields.value.type = 'text';
                    console.warn(`Unsupported model type: '${response.model_name}' for setting '${response.key}'`);
                }
            }

            constructChangeForm(fields, {
                url: url,
                method: 'PATCH',
                title: options.title,
                processResults: function(data, fields, opts) {
                    switch (data.type) {
                        case 'boolean':
                            // Convert to boolean value
                            data.value = data.value.toString().toLowerCase() == 'true';
                            break;
                        case 'integer':
                            // Convert to integer value
                            data.value = parseInt(data.value.toString());
                            break;
                        case 'decimal':
                            // Convert to integer value
                            data.value = parseFloat(data.value.toString());
                            break;
                        default:
                            break;
                    }

                    return data;
                },
                processBeforeUpload: function(data) {
                    // Convert value to string
                    data.value = data.value.toString();

                    return data;
                },
                onSuccess: function(response) {

                    var setting_pk = response.pk;
                    var setting_typ = response.typ;

                    if (reload_required) {
                        location.reload();
                    } else if (response.type == 'boolean') {
                        var enabled = response.value.toString().toLowerCase() == 'true';
                        $(`#setting-value-${setting_pk}-${setting_typ}`).prop('checked', enabled);
                    } else {
                        $(`#setting-value-${setting_pk}-${setting_typ}`).html(response.value);
                    }
                }
            });
        },
        error: function(xhr) {
            showApiError(xhr, url);
        }
    });
}
