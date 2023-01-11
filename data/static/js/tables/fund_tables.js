var callbackFund;
var callbackFundItem;

var fundPk=0;
var csrftoken=0;

function initializeFundTable(callback_fund=null, callback_funditem=null){
    callbackFund=callback_fund;
    callbackFundItem=callback_funditem;
    $('#project_fund_table').bootstrapTable({
        onLoadSuccess: function(){ updateFundBtnHandler();},
        onSearch: function(){ updateFundBtnHandler();},
        onSort: function(){  updateFundBtnHandler();},
        onToggle: function(){ updateFundBtnHandler();},
        onPageChange: function(){ updateFundBtnHandler();},
    });

}

function updateFund(){
    $('#project_fund_table').bootstrapTable('refresh');
    if(callbackFund!=null)callbackFund();
}
function updateFullFund(){
    $('#project_fund_table').bootstrapTable('refresh');
    $('#project_fund_item_table').bootstrapTable('refresh');
    $('#project_expense_timepoint_table').bootstrapTable('refresh');
    updateFundOverviewTableAjax(fundPk, csrftoken);
    if(callbackFundItem!=null)callbackFundItem();
}


function adminActionFund(value, row, index, field){
    action = "<span class='icon-left-cell btn-group'>";
    if(this.isStaff=='True')action += "<a href='/admin/fund/fund/"+row.pk+"/change/'><button class='icon admin_btn btn btn-primary'><i type = 'button' class='fas fa-shield-halved'></i></button></a>"
    if(this.canChange=='True')action += "<button class='icon edit_fund btn btn-success' data-form-url='/fund/ajax/"+row.pk+"/update' ><i type = 'button' class='fas fa-edit'></i></button>";
    action += "<button class='icon show_fund btn btn-secondary' data-fund='"+row.pk+"' ><i type = 'button' class='fas fa-toolbox'></i></button>";
    if(this.canDelete=='True')action += "<button class='icon delete_fund btn btn-danger ' data-form-url='/fund/ajax/"+row.pk+"/delete' ><i type = 'button' class='fas fa-trash'></i></button>";
    action += "</span>"
    return action;
}
function adminActionFundItem(value, row, index, field){
    action = "<span class='icon-left-cell btn-group'>";
    if(this.canChange=='True')action += "<button class='icon edit_fundItem btn btn-success' data-form-url='/fund/ajax/funditem/"+row.pk+"/update' ><i type = 'button' class='fas fa-edit'></i></button>";
    if(this.canDelete=='True')action += "<button class='icon delete_fundItem btn btn-danger ' data-form-url='/fund/ajax/funditem/"+row.pk+"/delete' ><i type = 'button' class='fas fa-trash'></i></button>";
    action += "</span>"
    return action;
}
function adminActionExpensePointdItem(value, row, index, field){
    action = "<span class='icon-left-cell btn-group'>";
    if(this.canChange=='True')action += "<button class='icon edit_ExpTpitem btn btn-success' data-form-url='/fund/ajax/expense_timepoint/"+row.pk+"/update' ><i type = 'button' class='fas fa-edit'></i></button>";
    if(this.canDelete=='True')action += "<button class='icon delete_ExpTpitem btn btn-danger ' data-form-url='/fund/ajax/expense_timepoint/"+row.pk+"/delete' ><i type = 'button' class='fas fa-trash'></i></button>";
    action += "</span>"
    return action;
}


function updateFundItem(){
    $('#project_fund_item_table').bootstrapTable({
        onLoadSuccess: function(){ updateFundItemBtnHandler();},
        onSearch: function(){ updateFundItemBtnHandler();},
        onSort: function(){  updateFundItemBtnHandler();},
        onToggle: function(){ updateFundItemBtnHandler();},
        onPageChange: function(){ updateFundItemBtnHandler();},
    });
    
    $('#add_fund_item_temp').modalForm({
        modalID: "#create-modal",
        modalContent: ".modal-content",
        modalForm: ".modal-content form",
        formURL: '/fund/ajax/funditem/add/' + $("#add_fund_item_temp").attr("data-fundPk"),
        isDeleteForm: false,
        errorClass: ".form-validation-warning",
        asyncUpdate: true,
        asyncSettings: {
            directUpdate: true,
            closeOnSubmit: true,
            successMessage: "Employee Updated",
            dataUrl: '/api/employee/',
            dataElementId: '#employee_main_table',
            dataKey: 'table',
            addModalFormFunction: updateFullFund,
        }
    });
}

function updateExpenseTimepoint(){
    $('#project_expense_timepoint_table').bootstrapTable({
        onLoadSuccess: function(){ updateExpenseTimepointBtnHandler();},
        onSearch: function(){ updateExpenseTimepointBtnHandler();},
        onSort: function(){  updateExpenseTimepointBtnHandler();},
        onToggle: function(){ updateExpenseTimepointBtnHandler();},
        onPageChange: function(){ updateExpenseTimepointBtnHandler();},
    });
    $('#add_expense_timepoint').modalForm({
        modalID: "#create-modal",
        modalContent: ".modal-content",
        modalForm: ".modal-content form",
        formURL: '/fund/ajax/expense_timepoint/add/' + $("#add_expense_timepoint").attr("data-fundPk"),
        isDeleteForm: false,
        errorClass: ".form-validation-warning",
        asyncUpdate: true,
        asyncSettings: {
            directUpdate: true,
            closeOnSubmit: true,
            successMessage: "Employee Updated",
            dataUrl: '/api/employee/',
            dataElementId: '#employee_main_table',
            dataKey: 'table',
            addModalFormFunction: updateFullFund,
        }
    });
}
function updateExpenseTimepointBtnHandler(){
    $(".edit_ExpTpitem").each(function () {
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
                successMessage: "Employee Updated",
                dataUrl: '/api/employee/',
                dataElementId: '#employee_main_table',
                dataKey: 'table',
                addModalFormFunction: updateFullFund,
            }
        });
    });
    $(".delete_ExpTpitem").each(function () {
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
                addModalFormFunction: updateFullFund,
            }
        });
    });
}

function updateFundItemBtnHandler(){
    $(".edit_fundItem").each(function () {
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
                successMessage: "Employee Updated",
                dataUrl: '/api/employee/',
                dataElementId: '#employee_main_table',
                dataKey: 'table',
                addModalFormFunction: updateFullFund,
            }
        });
    });
    $(".delete_fundItem").each(function () {
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
                addModalFormFunction: updateFullFund,
            }
        });
    });

}
// AJAX Function to update related tables
function updateFundItemTableAjax(fundPk, csrftoken){
    $.ajax({
        type:"POST",
        url: "/fund/ajax/"+fundPk+"/items/", 
        data:{
                pk:fundPk,
                csrfmiddlewaretoken: csrftoken,
        },
        success: function( data )
        {
            $('#fund_item_detail').html(data);
            updateFundItem();                    
        },
        error:function( err )
        {
            $("body").html(err.responseText)
            //console.log(JSON.stringify(err));
        }
    }) 
}
function updateFundOverviewTableAjax(fundPk, csrftoken){
    $.ajax({
        type:"POST",
        url: "/fund/"+fundPk+"/fundoverview/", 
        data:{
                pk:fundPk,
                csrfmiddlewaretoken: csrftoken,
        },
        success: function( data )
        {
            $('#fund_overview').html(data);
            updateFundItem();                    
        },
        error:function( err )
        {
            $("body").html(err.responseText)
            //console.log(JSON.stringify(err));
        }
    }) 
}
function updateFundExpenseTimepointTableAjax(fundPk, csrftoken){
    $.ajax({
        type:"POST",
        url: "/fund/"+fundPk+"/expense_timepoint/", 
        data:{
                pk:fundPk,
                csrfmiddlewaretoken: csrftoken,
        },
        success: function( data )
        {
            $('#fund_expense_timepoint_detail').html(data);
            updateExpenseTimepoint();                    
        },
        error:function( err )
        {
            $("body").html(err.responseText)
            //console.log(JSON.stringify(err));
        }
    }) 
}
function updateFundBtnHandler(){   

    $(".show_fund").each(function () {
        
            $(this).click(function(e){
                e.preventDefault();
                fundPk=$(this).data("fund");
                csrftoken = getCookie('csrftoken');
                // fund overview
                if($('#fund_overview').exists())updateFundOverviewTableAjax(fundPk, csrftoken);
                // Fund item
                if($('#fund_item_detail').exists())updateFundItemTableAjax(fundPk, csrftoken);
                if($('#fund_expense_timepoint_detail').exists())updateFundExpenseTimepointTableAjax(fundPk, csrftoken);
                // set the barck grod color
                rows=$(this).closest('tbody');
                rows.find('tr').each(function(){$(this).removeClass('select-row')});
                row=$(this).closest('tr');
                row.addClass('select-row');

            })
        

    });

    $(".edit_fund").each(function () {
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
                successMessage: "Employee Updated",
                dataUrl: '/api/employee/',
                dataElementId: '#employee_main_table',
                dataKey: 'table',
                addModalFormFunction: updateFund,
            }
        });
    });
    $(".delete_fund").each(function () {
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
                addModalFormFunction: updateFund,
            }
        });
    });
    if(isEmpty( $('#fund_item_detail') )){
        $(".show_fund").eq(0).trigger("click");
    }
   
}