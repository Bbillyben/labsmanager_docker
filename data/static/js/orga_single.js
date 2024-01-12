user_id = 0;
orga_id = 0;
orga_type="";

function initOrgaSingleView(user_idA, orga_idA, orga_typeA){
    user_id = user_idA;
    orga_id = orga_idA;
    orga_type=orga_typeA;
    var url = $('#edit-orga').data("url");
    $('#edit-orga').labModalForm({
        formURL:url,
        addModalFormFunction: function(){loadCards('orga');},
        modal_title:"Edit Organization",
    })

}


function updateInfoTableBtn(){
    $('#orga_infos_table').find('.update_info').each(function(){
        $(this).labModalForm({
            formURL:$(this).data('form-url'),
            addModalFormFunction: function(){loadInfosPanel();},
            modal_title:"Edit Organization Info",
            }
        )
    });

    $('#orga_infos_table').find('.delete_info').each(function(){
        $(this).labModalForm({
            formURL:$(this).data('form-url'),
            addModalFormFunction: function(){loadInfosPanel();},
            modal_title:"Delete Organization Info",
            isDeleteForm: true,

            }
        )
    });
    // for tooltip
    options={
        html:true,
        customClass:'availContTooltip',
    }
    $('#orga_infos_table').find('.availComment[data-bs-toggle="tooltip"]').each(function(){
       new bootstrap.Tooltip(this, options)
    });

    $("#info_create").labModalForm({
        formURL:$('#info_create').data("form-url"),
        addModalFormFunction: function(){loadInfosPanel();},
        modal_title:"Add Organization Info",
        }
    )
}
function loadInfosPanel(){
    loadCards('info', updateInfoTableBtn);

}


// #################### For Project Panel

function initProjectPanelOrga(){

    var filters = loadTableFilters('project_orga');
    var filterOption={
        download:false,
    }

    var options={
        url:$('#project_orga_table').data("url"),
        queryParams: filters,
        name:'project_orga',
    }
    setupFilterList('project_orga', $('#project_orga_table'),'#filter-list-project_orga', filterOption);
    $('#project_orga_table').labTable(options);
}



// #################### For Contact Panel
var contact=0;
function initContactPanel(){
    var filters = loadTableFilters('contact_orga');
    var filterOption={
        download:false,
    }
    var options={
        callback: updateContactSelection,
        onClickRow:contactRowclick,
        url:$('#contact_table').data("url"),
        queryParams: filters,
        name:'project_orga',
    }
    setupFilterList('contact_orga', $('#contact_table'),'#filter-list-contact_orga', filterOption);
    $('#contact_table').labTable(options);
    
    $("#contact_create").labModalForm({
        formURL:$("#contact_create").data("url"),
        addModalFormFunction: updateContactPanel,
        modal_title:"Add Organization Contact",
        }
    )

    updateContactPanel();

}
function updateContactPanel(){
    $('#contact_table').bootstrapTable('refresh');
    
}

function contactRowclick(row, element, field){
    contact=row["pk"];
    loadContactInfo(contact)
    makeTableRowSelect(element)
}

function updateContactSelection(){
    if(contact!=0){
        elt=getRowOrderByProperty('#contact_table', 'pk', contact);
        if (elt && elt[0]){
            makeTableRowSelect($('#contact_table tr').eq(elt[0]+1))
        }
    }
    options={
        html:true,
        customClass:'availContTooltip',
    }
    $('#contact_table').find('.availComment[data-bs-toggle="tooltip"]').each(function(){
       new bootstrap.Tooltip(this, options)
    });
}
function loadContactInfo(contact){
    loadInTemplate(
        elt=$('#contact_infos'),
        url=Urls['contact_info'](contact),
        data={},
        callback=updateContactInfoBtn,
    )
}
function updateContactInfoBtn(){
    $("#contact_info_create").labModalForm({
        formURL:$('#contact_info_create').data("form-url"),
        addModalFormFunction: function(){loadContactInfo(contact);},
        modal_title:"Add Contact Info",
        }
    )

    $('#orga_contact_infos_table').find('.update_info').each(function(){
        $(this).labModalForm({
            formURL:$(this).data('form-url'),
            addModalFormFunction: function(){loadContactInfo(contact);},
            modal_title:"Edit Organization Info",
            }
        )
    });

    $('#orga_contact_infos_table').find('.delete_info').each(function(){
        $(this).labModalForm({
            formURL:$(this).data('form-url'),
            addModalFormFunction: function(){loadContactInfo(contact);},
            modal_title:"Delete Organization Info",
            isDeleteForm: true,

            }
        )
    });

    options={
        html:true,
        customClass:'availContTooltip',
    }
    $('#orga_contact_infos_table').find('.availComment[data-bs-toggle="tooltip"]').each(function(){
       new bootstrap.Tooltip(this, options)
    });

}
function adminContactFormatter(value, row, index, field){
    action = "<span class='icon-left-cell btn-group'>";
    if(this.isStaff=='True')action += "<a href='"+Urls['admin:infos_contact_change'](row.pk)+"'><button class='icon admin_btn btn btn-primary'><i type = 'button' class='fas fa-shield-halved'></i></button></a>"
    if(this.canChange=="True")action += "<button class='icon edit btn btn-success' data-form-url='"+Urls['update_orgacontact'](row.pk)+"' ><i type = 'button' class='fas fa-edit'></i></button>";
    if(this.canDelete=="True")action += "<button class='icon delete btn btn-danger ' data-form-url='"+Urls['delete_orgacontact'](row.pk)+"' ><i type = 'button' class='fas fa-trash'></i></button>";
    action += "</span>"
    return action;
}

function typeContactFormatter(value, row, index, field){
    response = value;
    if (row.comment && row.comment != "None"){
        response += '<span class="availComment" tabindex="0" data-bs-toggle="tooltip" data-bs-placement="right" title="'+row.comment+'"><span class="aicon fa fa-comment"> </span></span>'
    }
    return response;
}