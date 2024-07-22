
var callbackMs;


function initializeMilestoneTable(tableurl, type=null, callback_ms=null){
    callbackMs=callback_ms;

    var options={
        //callback: updateMilestonesBtnHandler,
        url:tableurl,
        name:'milestones',
        
    }
    if(type!='project'){
        var filters = loadTableFilters('contract');
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


// ------------- Formatters ---------------------------------------------- //

function adminActionMilestones(value, row, index, field){
    action = "<span class='icon-left-cell btn-group'>";
    if(this.canChange=='True' || row.has_perm==true)action += "<button class='icon edit btn btn-success' data-form-url='/milestones/"+row.pk+"/update/' ><i type = 'button' class='fas fa-edit'></i></button>";
    if(this.canDelete=='True')action += "<button class='icon delete btn btn-danger ' data-form-url='/milestones/"+row.pk+"/delete/' ><i type = 'button' class='fas fa-trash'></i></button>";
    action += "</span>"
    return action;
}

// ------------- Update Function ---------------------------------------------- //
function updateMilestones(){
    $('#milestones_table').bootstrapTable('refresh');
    if(callbackMs!=undefined){
        callbackMs();
    }
}

