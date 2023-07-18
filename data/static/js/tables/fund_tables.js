var callbackFund;
var callbackFundItem;

var fundPk=0;
var csrftoken=0;

function initializeFundTable(callback_fund=null, callback_funditem=null){
    callbackFund=callback_fund;
    callbackFundItem=callback_funditem;

    var options={
        url:$('#project_fund_table').data("url"),
        name:'fund',
        disablePagination:true,
        search:false,
        showColumns:false,
        onClickRow:fundRowclick, 
        callback:updateFundSelection,

        
    }

    $('#project_fund_table').labTable(options);

}
function fundRowclick( row, element, field){
    fundPk=row["pk"];
    csrftoken = getCookie('csrftoken');
    // fund overview
    if($('#fund_overview').exists())updateFundOverviewTableAjax(fundPk, csrftoken);
    // Fund item
    if($('#fund_item_detail').exists())updateFundItemTableAjax(fundPk, csrftoken);
    if($('#fund_expense_timepoint_detail').exists())updateFundExpenseTimepointTableAjax(fundPk, csrftoken);
    makeTableRowSelect(element);
}
function updateFundSelection(){
    if(fundPk!=0){
        elt=getRowOrderByProperty('#project_fund_table', 'pk', fundPk);
        if (elt && elt[0]){
            makeTableRowSelect($('#project_fund_table tr').eq(elt[0]+1))
        }
    }
}
function updateFund(){
    $('#project_fund_table').bootstrapTable('refresh');
    if(callbackFund!=null)callbackFund();
}
function updateFullFund(){
    $('#project_fund_table').bootstrapTable('refresh');
    $('#project_fund_item_table').bootstrapTable('refresh');
    //$('#project_expense_timepoint_table').bootstrapTable('refresh');
    updateFundOverviewTableAjax(fundPk, csrftoken);
    if(callbackFundItem!=null)callbackFundItem();
}
function updageGlobalFund(){
    updateFullFund();
    $('#project_expense_timepoint_table').bootstrapTable('refresh');
}


function adminActionFund(value, row, index, field){
    action = "<span class='icon-left-cell btn-group'>";
    if(this.isStaff=='True')action += "<a href='/admin/fund/fund/"+row.pk+"/change/'><button class='icon admin_btn btn btn-primary'><i type = 'button' class='fas fa-shield-halved'></i></button></a>"
    if(this.canChange=='True')action += "<button class='icon edit btn btn-success' data-form-url='/fund/ajax/"+row.pk+"/update' ><i type = 'button' class='fas fa-edit'></i></button>";
    //action += "<button class='icon show_fund btn btn-secondary' data-fund='"+row.pk+"' ><i type = 'button' class='fas fa-toolbox'></i></button>";
    if(this.canDelete=='True')action += "<button class='icon delete btn btn-danger ' data-form-url='/fund/ajax/"+row.pk+"/delete' ><i type = 'button' class='fas fa-trash'></i></button>";
    action += "</span>"
    return action;
}
function adminActionFundItem(value, row, index, field){
    action = "<span class='icon-left-cell btn-group'>";
    if(this.canChange=='True')action += "<button class='icon edit btn btn-success' data-form-url='/fund/ajax/funditem/"+row.pk+"/update' ><i type = 'button' class='fas fa-edit'></i></button>";
    if(this.canDelete=='True')action += "<button class='icon delete btn btn-danger ' data-form-url='/fund/ajax/funditem/"+row.pk+"/delete' ><i type = 'button' class='fas fa-trash'></i></button>";
    action += "</span>"
    return action;
}
function adminActionExpensePointdItem(value, row, index, field){
    action = "<span class='icon-left-cell btn-group'>";
    if(this.canChange=='True')action += "<button class='icon edit btn btn-success' data-form-url='/fund/ajax/expense_timepoint/"+row.pk+"/update' ><i type = 'button' class='fas fa-edit'></i></button>";
    if(this.canDelete=='True')action += "<button class='icon delete btn btn-danger ' data-form-url='/fund/ajax/expense_timepoint/"+row.pk+"/delete' ><i type = 'button' class='fas fa-trash'></i></button>";
    action += "</span>"
    return action;
}


function updateFundItem(){
    var options={
        url:$('#project_fund_item_table').data("url"),
        name:'fund_item',
        disablePagination:true,
        search:false,
        showColumns:false,
        callback:updateFund,
        playCallbackOnLoad:false,
        
    }
    $('#project_fund_item_table').labTable(options)
    
    $('#add_fund_item_temp').labModalForm({
            formURL: '/fund/ajax/funditem/add/' + $("#add_fund_item_temp").attr("data-fundPk"),
            addModalFormFunction: updateFullFund,
            modal_title:"Add",
        })
}

function updateExpenseTimepoint(){
    var options={
        url:$('#project_expense_timepoint_table').data("url"),
        name:'expense_timepoint',
        disablePagination:true,
        search:false,
        showColumns:false,
        callback:updateFullFund,
        playCallbackOnLoad:false,
        
    }

    $('#project_expense_timepoint_table').labTable(options)
    $('#add_expense_timepoint').labModalForm({
        formURL: '/fund/ajax/expense_timepoint/add/' + $("#add_expense_timepoint").attr("data-fundPk"),
        addModalFormFunction: updageGlobalFund,
        modal_title:"Add",
    })
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