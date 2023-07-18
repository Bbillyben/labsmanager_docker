user_id= 0;
function initContractBaseView(user_idA){
    user_id = user_idA;

    
    $('#contract_create').labModalForm({
        formURL:'/expense/ajax/contract/add/',
        addModalFormFunction: updateContract,
        modal_title:"Add Contract",
    })

}