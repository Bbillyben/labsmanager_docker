var callbackContract;
var callbackContractExpense;
var contract=0;
function initializeContractsTable(tableurl, callback_contract=undefined, callback_contractExpense=undefined, extra_params=null){
    callbackContract=callback_contract;
    callbackContractExpense=callback_contractExpense;
    // get table filter name
    var fName = $('#contract_table').data('toolbar');
    if(fName != undefined){
        fName = fName.replace("#tracking-table-toolbar_",'');
        // console.log("[initializeContractsTable] filter name :"+fName);
        var filters = loadTableFilters(fName);
        var filterOption={
            download:true,
        }
    }
    
    var options={
            callback: updateContractSelection,
            url:tableurl,
            queryParams: filters,
            name:'contract',
            onClickRow:contractRowclick, 
            extra_params: extra_params,
            
        }
    if(fName != undefined)setupFilterList(fName, $('#contract_table'), '#filter-list-'+fName, filterOption );
    $('#contract_table').labTable(options);

}

function contractRowclick(row, element, field){
    contract=row["pk"];
    loadContractExpense(contract)
    makeTableRowSelect(element)
}
// ------------- Formatters ---------------------------------------------- //

/// contract Table

function adminActionContract(value, row, index, field){
    //console.log("adminActionContract   ------------------------------------------------------------------------------------------------- ")

    action = "<span class='icon-left-cell btn-group'>";
    if(this.isStaff=='True')action += "<a href='/admin/expense/contract/"+row.pk+"/change/'><button class='icon admin_btn btn btn-primary'><i type = 'button' class='fas fa-shield-halved'></i></button></a>"
    if(this.canChange=='True' || row.has_perm==true)action += "<button class='icon edit btn btn-success' data-form-url='/expense/ajax/contract/"+row.pk+"/update' ><i type = 'button' class='fas fa-edit'></i></button>";
    //action += "<button class='icon show_contract btn btn-secondary' data-contract='"+row.pk+"' ><i type = 'button' class='fas fa-toolbox'></i></button>";
    if(this.canDelete=='True')action += "<button class='icon delete btn btn-danger ' data-form-url='/expense/ajax/contract/"+row.pk+"/delete' ><i type = 'button' class='fas fa-trash'></i></button>";
    action += "</span>"
    return action;
}
/// contract Expense Table
function adminContractExpenseFormatter(value, row, index, field){
    action = "<span class='icon-left-cell btn-group'>";
    if(this.canChange=='True' || row.has_perm==true )action += "<button class='icon edit btn btn-success' data-form-url='/expense/ajax/contractitem/"+row.pk+"/update' ><i type = 'button' class='fas fa-edit'></i></button>";
    if(this.canDelete=='True')action += "<button class='icon delete btn btn-danger ' data-form-url='/expense/ajax/contractitem/"+row.pk+"/delete' ><i type = 'button' class='fas fa-trash'></i></button>";
    action += "</span>";
    return action;
}


// ------------- Update Function ---------------------------------------------- //

// called for contract update Table
function updateContract(){
    $('#contract_table').bootstrapTable('refresh');
    if(callbackContract!=undefined){
        callbackContract();
    }
    
}
function updateContractSelection(){
    if(contract!=0){
        elt=getRowOrderByProperty('#contract_table', 'pk', contract);
        if (elt && elt[0]){
            makeTableRowSelect($('#contract_table tr').eq(elt[0]+1))
        }
    }
}
function updateContractExpense(){
    $("#project_contract_item_table").bootstrapTable('refresh');
    updateContract();
    if(callbackContractExpense){
        callbackContractExpense();
    }
}
function loadContractExpense(contract){
    csrftoken = getCookie('csrftoken');
    $.ajax({
        type:"POST",
        url: "/expense/ajax/"+contract+"/contract_expense/", 
        data:{
                pk:contract,
                csrfmiddlewaretoken: csrftoken,
        },
        success: function( data )
        {
            $('#contract_expense_detail').html(data);
            updateContractItem();                    
        },
        error:function( err )
        {
                $("body").html(err.responseText)
            //console.log(JSON.stringify(err));
        }
    }) 
}
function updateContractItem(){
    var options={
        callback: updateContract,
        url:$('#project_contract_item_table').data('url'),
        //queryParams: filters,
        name:'contract_expense',
        search:false,
        showColumns:false,
        disablePagination:true,
        playCallbackOnLoad:false,
    }
    $('#project_contract_item_table').labTable(options);

    $('#add_contract_expense').unbind();
    $('#add_contract_expense').labModalForm({
        formURL:   '/expense/ajax/contract_expense/add/'+$('#add_contract_expense').attr('data-contractPk'),
        addModalFormFunction: updateContractExpense,
        modal_title:"Add",
    })


}