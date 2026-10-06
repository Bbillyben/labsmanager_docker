var callbackContrib;
var tableContribType;
var tableContribPk;
function initializeContribTable(callback=null){
    callbackContrib=callback;

    tableContribType=$("#contrib_table").data("type")
    tableContribPk=$("#contrib_table").data("pk")
  // get table filter name
  var fName = $('#contrib_table').data('toolbar');
  if(fName != undefined){
      fName = fName.replace("#tracking-table-toolbar_",'');
      var filters = loadTableFilters(fName);
      var filterOption={
          download:true,
      }
  }
    var options={
        queryParams: filters,
        name:'contrib',
        
    }
    if(callbackContrib!=null)options['callback']=callbackContrib;

    setupFilterList(fName, $('#contrib_table'), '#filter-list-'+fName,filterOption);
    $('#contrib_table').labTable(options);


    switch (tableContribType) {
        case 'project':
          urlmodal=Urls['add_contribution_project'](tableContribPk);
          break;
        case 'employee':
            urlmodal=Urls['add_contribution_employee'](tableContribPk);
            break;
        case 'team':
            urlmodal=Urls['add_contribution_team'](tableContribPk);
            break;
        case 'search':
            urlmodal=false;
            break;
        default:
            urlmodal=false;
          console.log(`[initializeContribTable] type not found : ${tableContribType}`);
      }
      if(urlmodal && $('#add_contrib').length){
            // button ajout
            $('#add_contrib').labModalForm({
                formURL:urlmodal,
                addModalFormFunction: updateFullContrib,
                modal_title:"Add",
            })
      }
    

}
function updateFullContrib(){
    $('#contrib_table').bootstrapTable('refresh');
    if(callbackContrib!=null)callbackContrib();
}

function adminActioncontrib(value, row, index, field){
    action = "<span class='icon-left-cell btn-group'>";
    if(this.isStaff=='True')action += "<a href='"+Urls["admin:fund_contribution_change"](row.pk)+"'><button class='icon admin_btn btn btn-primary'><i type = 'button' class='fas fa-shield-halved'></i></button></a>"
    if(this.canChange=='True' || row.has_perm==true)action += "<button class='icon edit btn btn-success' data-form-url='"+Urls['update_contribution'](row.pk)+"' ><i type = 'button' class='fas fa-edit'></i></button>";
    if(this.canDelete=='True')action += "<button class='icon delete btn btn-danger ' data-form-url='"+Urls['delete_contribution'](row.pk)+"' ><i type = 'button' class='fas fa-trash'></i></button>";
    action += "</span>"
    return action;
}