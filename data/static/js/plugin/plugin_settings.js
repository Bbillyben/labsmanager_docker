function initialize_plugin_list(){
    var filters = loadTableFilters('plugin');
    var filterOption={
        download:false,
    }
    var options={
        callback:update_pg_list_btn,
        url:Urls["api-plugin-list"](),
        queryParams: filters,
        name:'plugin',        
    }
    setupFilterList('plugin', $('#plugin-table'), '#filter-list-plugin',  filterOption);


    $('#plugin-table').labTable(options);

    // Callback to reload plugins
    $('#reload-plugins').click(function() {
        console.log(" ######## reload-plugins ##########")
        reloadPlugins();
    });
}
function update_pg_list(){
    $('#plugin-table').bootstrapTable('refresh');
}
function update_pg_list_btn(){
    $('#plugin-table').on('click', '.btn-plugin-enable', function() {
        let pk = $(this).data('pk');
        let key = $(this).data('key');
        console.log("btn-plugin-enable click :"+pk+" / "+key)
        activatePlugin(key, true);
    });
    $('#plugin-table').on('click', '.btn-plugin-disable', function() {
        let pk = $(this).data('pk');
        let key = $(this).data('key');
        console.log("btn-plugin-enable click :"+pk+" / "+key)
        activatePlugin(key, false);
    });

}

/*   FOrmatters   */
function pg_name_formatter(value, row, index, field){
    response = ""
    if(row.active){
        response +='<i class="fa fa-check-circle fa-w-16 icon-green"></i>';
    }else{
        response +='<i class="fa fa-question-circle fa-w-16"></i>';
    }
    response += '<span class="pg-name">'+value+"</span>";
    if(row.is_builtin){
        response += '<span class="badge bg-success rounded-pill badge-right" >'+"builtin"+"</span>";
    }
    if(row.is_sample){
        response += '<span class="badge bg-warning rounded-pill badge-right" >'+"sample"+"</span>";
    }

    return response;
}

function pg_action_formatter(value, row, index, field){
    if (row.is_builtin)return '';
    response = ""
    if (row.active) {
        response += "<i class='fa fa-stop-circle icon-red btn-plugin-disable'  data-pk='"+row.pk+"' data-key='"+row.key+"' title='Disable Plugin'></i>";
    } else {
        response += "<i class='fa fa-play-circle icon-green btn-plugin-enable' data-pk='"+row.pk+"' data-key='"+row.key+"' title='Enable Plugin'></i>";
    }
    return response;
}

function pg_mixin_formatter(value, row, index, field){
    response = ""
    for( mixin in value){
        response+= ((response.length)>1?", ":"")+value[mixin].human_name
    }
    return "<i>"+response+"</i>";
}

/* btn actions */
function reloadPlugins() {
    let url = Urls["api-plugin-reload"]();
    console.log("reload url : "+url)

    constructForm(url, {
        title: 'Reload Plugins',
        method: 'POST',
        confirm: true,
        fields: {
            force_reload: {
                // hidden: true,
                value: true,
            },
            full_reload: {
                // hidden: true,
                value: true,
            },
            collect_plugins: {
                // hidden: true,
                value: true,
            },
        },
        onSuccess: function() {
            location.reload();
        }
    });
}

function activatePlugin(plugin_id, active=true) {

    let url =Urls['api-plugin-detail-activate'](plugin_id);

    let html = active ? `
    <span class='alert alert-block alert-info'>
    Are you sure you want to enable this plugin?
    </span>
    ` : `
    <span class='alert alert-block alert-danger'>
    Are you sure you want to disable this plugin?
    </span>
    `;

    constructForm(null, {
        title: active ? 'Enable Plugin' : 'Disable Plugin',
        preFormContent: html,
        confirm: true,
        submitText: active ? 'Enable' : 'Disable',
        submitClass: active ? 'success' : 'danger',
        onSubmit: function(_fields, opts) {
            showModalSpinner(opts.modal);

            labsmanagerPut(
                url,
                {
                    active: active,
                },
                {
                    method: 'PATCH',
                    success: function() {
                        $(opts.modal).modal('hide');
                        showMessage('Plugin updated', {style: 'success'});
                        location.reload();
                    },
                    error: function(xhr) {
                        $(opts.modal).modal('hide');
                        showApiError(xhr, url);
                    }
                }
            )
        }
    });
}