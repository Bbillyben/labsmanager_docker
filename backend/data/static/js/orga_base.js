user_id = 0;

function initInstitutionBaseView(tableurl, user_idA){
    user_id = user_idA;
    var options={
        url:tableurl,
        name:'institution',
    }
    $('#institution_main_table').labTable(options);

    $('#add_institution').labModalForm({
        formURL:Urls['add_institution_direct'](),
        addModalFormFunction: function(){$('#institution_main_table').bootstrapTable('refresh');},
        modal_title:"Create Institution",
    })


}
function initFunderBaseView(tableurl, user_idA){
    user_id = user_idA;
    var options={
        url:tableurl,
        name:'institution',
    }
    $('#funder_main_table').labTable(options);

    $('#add_funder').labModalForm({
        formURL:Urls['add_fundinstitution'](),
        addModalFormFunction: function(){$('#funder_main_table').bootstrapTable('refresh');},
        modal_title:"Create Funder",
    })
}


function InstutionActionFormatter(value, row, index, field){
    action = "<span class='icon-left-cell btn-group'>";
    if(this.isStaff=='True')action += "<a href='"+Urls['admin:project_institution_change'](row.pk)+"'><button class='icon admin_btn btn btn-primary'><i type = 'button' class='fas fa-shield-halved'></i></button></a>"
    if(this.canChange=="True")action += "<button class='icon edit btn btn-success' data-form-url='"+Urls['update_project_institution'](row.pk)+"' ><i type = 'button' class='fas fa-edit'></i></button>";
    action += "</span>"
    return action;
  }

  function funderActionFormatter(value, row, index, field){
    action = "<span class='icon-left-cell btn-group'>";
    if(this.isStaff=='True')action += "<a href='"+Urls['admin:fund_fund_institution_change'](row.pk)+"'><button class='icon admin_btn btn btn-primary'><i type = 'button' class='fas fa-shield-halved'></i></button></a>"
    if(this.canChange=="True")action += "<button class='icon edit btn btn-success' data-form-url='"+Urls['update_fund_fund_institution'](row.pk)+"' ><i type = 'button' class='fas fa-edit'></i></button>";
    action += "</span>"
    return action;
  }
  