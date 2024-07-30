function initSettingsPage(){
    $('table').find('.boolean-setting').unbind().change(function() {
        var pk = $(this).attr('pk');
        var setting = $(this).attr('setting');
        var plugin = $(this).attr('plugin');
        var user = $(this).attr('user');
        var project = $(this).attr('project');
        var notification = $(this).attr('notification');

        var checked = this.checked;

        // Global setting by default
        var url = `/api/settings/global/${setting}/`;

        if  (user) {
            url = `/api/settings/user/${setting}/`;
        }

        if  (project) {
            url = `/api/settings/project/${setting}/`;
        }

        var data = {
            value: checked.toString(),
        }
        if (project){
            data.project = project;
        }
        labsmanagerPut(
            url, data,
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
    $('table').find('.btn-edit-setting').unbind().click(function() {
        var setting = $(this).attr('setting');
        var plugin = $(this).attr('plugin');
        var is_global = true;
        var notification = $(this).attr('notification');
        var user = $(this).attr('user')
        var project = $(this).attr('project')
        if (user || project){
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
        } else if(user) {
            title = 'Edit User Setting';
        }else {
            title = 'Edit Project Setting';
        }
        var options = { 
            plugin: plugin,
            global: is_global,
            notification: notification,
            title: title,
        }
        data={}
        if(project){
            data.project = project;
            options.project = project;
            options.reload_required = false
        }
        editSetting(setting,options, data);
    });

}

function getDisplayNameByValue(choicelist, value) {
    const choice = choicelist.find(choice => choice.value === value);
    return choice ? choice.display_name : null;
  }

/*
 * Interactively edit a setting value.
 * Launches a modal dialog form to adjut the value of the setting.
 */
function editSetting(key, options={}, data={}) {


    var  url = '';

    if (options.global) {
        url = `/api/settings/global/${key}/`;
    } else if(options.project){
        url = `/api/settings/project/${key}/`;
    } else {
        url = `/api/settings/user/${key}/`;
    }
    // First, read the settings object from the server
    labsmanagerGet(url, data, {
        success: function(response) {
            reload_required = true;
            if (response.choices && response.choices.length > 0) {
                response.type = 'choice';
                reload_required = true;
            }
            if(options.hasOwnProperty("reload_required"))reload_required = options.reload_required

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
                params:data,
                data:data,
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
                    showMessage("Setting Updated");
                    var setting_pk = response.pk;
                    var setting_type = response.type;

                    if (reload_required) {
                        location.reload();
                    } else if (response.type == 'boolean') {
                        var enabled = response.value.toString().toLowerCase() == 'true';
                        $(`#setting-value-${setting_pk}-${setting_type}`).prop('checked', enabled);
                    } else if(response.hasOwnProperty("choices")){
                        value = response.value;
                        display_name = getDisplayNameByValue(response.choices, value);
                        $(`#setting-value-${setting_pk}-${setting_type}`).html(display_name);
                    }else{
                        $(`#setting-value-${setting_pk}-${setting_type}`).html(response.value);
                    }
                }
            });
        },
        error: function(xhr) {
            showApiError(xhr, url);
        }
    });
}
