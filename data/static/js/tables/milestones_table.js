
var callbackMs;


function initializeMilestoneTable(tableurl, type=null, callback_ms=null){
    callbackMs=callback_ms;

    var options={
        callback: updateMilestonesBtnHandler,
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

    $('#add_milestones').modalForm({
        modalID: "#create-modal",
        modalContent: ".modal-content",
        modalForm: ".modal-content form",
        formURL: $('#add_milestones').attr("data-form-url"),
        isDeleteForm: false,
        errorClass: ".form-validation-warning",
        asyncUpdate: true,
        asyncSettings: {
            directUpdate: true,
            closeOnSubmit: true,
            successMessage: "Milestones Updated",
            dataUrl: '/api/Milestones/',
            dataElementId: '#add_milestones',
            dataKey: 'table',
            addModalFormFunction: updateMilestones,
        }
    });


}


// ------------- Formatters ---------------------------------------------- //

function adminActionMilestones(value, row, index, field){
    //console.log("adminActionContract   ------------------------------------------------------------------------------------------------- ")

    action = "<span class='icon-left-cell btn-group'>";
    if(this.canChange=='True')action += "<button class='icon edit_milestones btn btn-success' data-form-url='/milestones/"+row.pk+"/update/' ><i type = 'button' class='fas fa-edit'></i></button>";
    if(this.canDelete=='True')action += "<button class='icon delete_milestones btn btn-danger ' data-form-url='/milestones/"+row.pk+"/delete/' ><i type = 'button' class='fas fa-trash'></i></button>";
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

function updateMilestonesBtnHandler(){
    $(".edit_milestones").each(function () {
        $(this).modalForm({
            modalID: "#create-modal",
            modalContent: ".modal-content",
            modalForm: ".modal-content form",
            formURL: $(this).data("form-url"),
            isDeleteForm: false,
            errorClass: ".form-validation-warning",
            asyncUpdate: true,
            asyncSettings: {
                directUpdate: true,
                closeOnSubmit: true,
                successMessage: "Milestones Updated",
                dataUrl: '/api/Milestones/',
                dataElementId: '#employee_main_table',
                dataKey: 'table',
                addModalFormFunction: updateMilestones,
            }
        });
    });
    $(".delete_milestones").each(function () {
        $(this).modalForm({
            modalID: "#create-modal",
            modalContent: ".modal-content",
            modalForm: ".modal-content form",
            formURL: $(this).data("form-url"),
            isDeleteForm: true,
            errorClass: ".form-validation-warning",
            asyncUpdate: true,
            asyncSettings: {
                directUpdate: true,
                closeOnSubmit: true,
                successMessage: "Employee Updated",
                dataUrl: '/api/employee/',
                dataElementId: '#employee_main_table',
                dataKey: 'table',
                addModalFormFunction: updateMilestones,
            }
        });
    });
    
};