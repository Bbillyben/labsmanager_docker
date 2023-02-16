var callbackContract;
var callbackContractExpense;

function initializeContractsTable(tableurl, callback_contract=undefined, callback_contractExpense=undefined){
    callbackContract=callback_contract;
    callbackContractExpense=callback_contractExpense;

    var filters = loadTableFilters('contract');
    var filterOption={
        download:true,
    }
    var options={
            callback: updateContractBtnHandler,
            url:tableurl,
            queryParams: filters,
            name:'contract',
            
        }
    setupFilterList('contract', $('#contract_table'), '#filter-list-contract', filterOption );
    $('#contract_table').labTable(options);

}


// ------------- Formatters ---------------------------------------------- //

/// contract Table

function adminActionContract(value, row, index, field){
    //console.log("adminActionContract   ------------------------------------------------------------------------------------------------- ")

    action = "<span class='icon-left-cell btn-group'>";
    if(this.isStaff=='True')action += "<a href='/admin/expense/contract/"+row.pk+"/change/'><button class='icon admin_btn btn btn-primary'><i type = 'button' class='fas fa-shield-halved'></i></button></a>"
    if(this.canChange=='True')action += "<button class='icon edit btn btn-success' data-form-url='/expense/ajax/contract/"+row.pk+"/update' ><i type = 'button' class='fas fa-edit'></i></button>";
    action += "<button class='icon show_contract btn btn-secondary' data-contract='"+row.pk+"' ><i type = 'button' class='fas fa-toolbox'></i></button>";
    if(this.canDelete=='True')action += "<button class='icon delete btn btn-danger ' data-form-url='/expense/ajax/contract/"+row.pk+"/delete' ><i type = 'button' class='fas fa-trash'></i></button>";
    action += "</span>"
    return action;
}
/// contract Expense Table
function adminContractExpenseFormatter(value, row, index, field){
    action = "<span class='icon-left-cell btn-group'>";
    if(this.canChange=='True')action += "<button class='icon edit btn btn-success' data-form-url='/expense/ajax/contractitem/"+row.pk+"/update' ><i type = 'button' class='fas fa-edit'></i></button>";
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
function updateContractExpense(){
    $("#project_contract_item_table").bootstrapTable('refresh');
    updateContract();
    if(callbackContractExpense){
        callbackContractExpense();
    }
}

function updateContractBtnHandler(){
    $(".show_contract").each(function () {

        $(this).click(function(e){
            e.preventDefault();
            contract=$(this).data("contract");
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
            // set the barck grod color
            rows=$(this).closest('tbody');
            rows.find('tr').each(function(){$(this).removeClass('select-row')});
            row=$(this).closest('tr');
            row.addClass('select-row');

        })
    });

    // to select the first contract to show items on first load
    if(isEmpty( $('#contract_expense_detail') )){
        $(".show_contract").eq(0).trigger("click");
    }
    
}

function updateContractItem(){
    var options={
        callback: updateContract,
        url:$('#project_contract_item_table').data('url'),
        //queryParams: filters,
        name:'contract',
        search:false,
        showColumns:false,
        disablePagination:true,
    }
    $('#project_contract_item_table').labTable(options);

    $('#add_contract_expense').unbind();
    $('#add_contract_expense').labModalForm({
        formURL:   '/expense/ajax/contract_expense/add/'+$('#add_contract_expense').attr('data-contractPk'),
        addModalFormFunction: updateContractExpense,
    })


}