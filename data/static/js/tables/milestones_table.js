
var callbackMs;


function initializeMilestoneTable(tableurl, type=null, callback_ms=null){
    callbackMs=callback_ms;

    var options={
        // callback: updateMilestonesBtnHandler,
        url:tableurl,
        name:'milestones',
        onClickRow:milestoneRowclick, 
        
    }
    if(type!='project' &&  type!='employee'){
        var filters = loadTableFilters('milestones');
        var filterOption={
            download:true,
        }
        options["queryParams"]=filters;
        setupFilterList('milestones', $('#milestones_table'), '#filter-list-milestones', filterOption );
    }
    $('#milestones_table').labTable(options);
    $('#add_milestones').labModalForm({
        formURL: $('#add_milestones').attr("data-form-url"),
        addModalFormFunction: updateMilestones,
        modal_title:"Add",
    });


}

function milestoneRowclick(row, element, field){
    pk=row["pk"];
    loadInTemplate(elt=$("#milestones_notes"),Urls['generic_info_template']('endpoints', 'milestones', pk) )
    makeTableRowSelect(element);
}


// ------------- Formatters ---------------------------------------------- //

function adminActionMilestones(value, row, index, field){
    action = "<span class='icon-left-cell btn-group'>";
    if(this.canChange=='True' || row.has_perm==true || row.can_edit)action += "<button class='icon edit btn btn-success' data-form-url='/milestones/"+row.pk+"/update/' ><i type = 'button' class='fas fa-edit'></i></button>";
    if(this.canDelete=='True')action += "<button class='icon delete btn btn-danger ' data-form-url='/milestones/"+row.pk+"/delete/' ><i type = 'button' class='fas fa-trash'></i></button>";
    action += "</span>"
    return action;
}
function hasnoteformatter(value, row, index, field){
    action = value;
    if(row.notes>0)action += '<sup class="icon-spaced">'+row.notes+' <i class="fa fa-note-sticky "></i></sup>'
    return action
}
function descriptionFormatter(value, row, index, field){
    action = "<i><small>"+value+"</small></i>";
    return action
}
// ------------- Update Function ---------------------------------------------- //
function updateMilestones(){
    $('#milestones_table').bootstrapTable('refresh');
    if(callbackMs!=undefined){
        callbackMs();
    }
}

