user_id= 0;
function initContractBaseView(user_idA){
    user_id = user_idA;

    
    $('#contract_create').labModalForm({
        formURL:'/expense/ajax/contract/add/',
        addModalFormFunction: updateContract,
        modal_title:"Add Contract",
    })
    initializeContractsTable(tableurl='/api/contract/');

}


function initializeProspectiveView(user_idA){


    var filters = loadTableFilters('funditem_contract');
    // console.log('[initializeProspectiveView] :'+JSON.stringify(filters))
    var filterOption={
        download:false,
    }
    var options={
        queryParams: filters,
        name:'contractfunditem',
        showColumns:false,
        post_body_callback:updateFundItemDrag,
        
    }
    setupFilterList('funditem_contract', $('#contract_funditem_table'), '#filter-list-contractfunditem',filterOption);
    $('#contract_funditem_table').labTable(options);

    // calendar initialisation
    var canMod=USER_PERMS.includes("expense.change_contract") || USER_PERMS.includes("is_staff");
    option={
        selectable:canMod,
        editable:canMod,
        extraParams:{},
    }
    calendar = $('#contrat_calendar').lab_contract_prov(option)

}

function updateFundItemDrag(){
    let containerEl = document.getElementById('contract_funditem_table');
    $(containerEl).find(".contract_funditem").each(function(){
        new FullCalendar.Draggable(this);
    })
    $(".card-title .show_contract_fund").each(function(){
        $(this).labModal({
            templateURL:  $(this).data("form-url"),
            modal_title:"Infos",
        })
    })
    
    // new FullCalendar.Draggable(containerEl, {
    //     itemSelector: '.contract_funditem'
    //   });
}

function funditem_DnD_formatter(value, row, index, field){
    // console.log(JSON.stringify(row))
    active = (row.fund.is_active);
    var amount = row.fund.available;
    if(row.amount_left_effective || row.amount_left_prov)amount = amount - row.amount_left_effective - row.amount_left_prov;

    row["create"]=false;
    active_html = (active ? '<img src="/static/admin/img/icon-yes.svg" alt="True">' : '<img src="/static/admin/img/icon-no.svg" alt="False">');
    html= "";
    html += "<div class='card contract_funditem' data-event='"+JSON.stringify(row)+"'>";
    html += '<div class="card-body">';
    html += '<h6 class="card-title">';
    if(amount<=0)html +='<span class="text-danger"><i class="fa-solid fa-triangle-exclamation"></i></span>';
    html +=row.fund.project.name;

    html += "<sup><button class='show_contract_fund btn' data-form-url='"+Urls["api:contract-contract_fund_modal"](row.fund.pk)+"'><i class='fa-solid fa-circle-info'></i></button></sup> "
    html +='<span class="card_active" style="float:right;">'+active_html+'</span>';
    
    html += "</h6>";
    html += '<div><p class="card-text fund-dates"><i>'+row.fund.start_date +' -> '+row.fund.end_date+ '</i></p></div>';
    html += '<div class="card-title row">';
    html += '<div class="col col-sd-6">';
    html += '<div> <b>'+row.type.short_name+'</b></div>';
    html += '<div class="row"><p class="card-title">'+row.fund.funder.short_name+' / '+row.fund.institution.short_name+"</p></div>";
   
    html += '</div>';
    html +='<div class="col col-sd-6">';
    html +='<div class="fund-avail"> Total :'+moneyDisplay(row.fund.available)+'</div>';
    html +='<div class="fund-avail row"><small> (line :'+moneyDisplay(row.available)+')</small></div>';
    if(row.amount_left_effective || row.amount_left_prov){
        html +='<div class="fund-avail row '+(amount<=0?"text-danger":"")+'"><small>'+(moneyDisplay(amount))+'<small></div>'
    }
    html +='</div>';
    html +='<div class="col col-sd-6">';

    if(row.contract_effective){
        
        html +='<div class ="fund-cont"><span class="availContractCal effe" tabindex="0"><span class="aicon fa fa-file-signature"> </span><span class="anum">'+row.contract_effective+"</span></span>";
        if(row.amount_left_effective)html +='<span class="amount">'+moneyDisplay(row.amount_left_effective)+'</span>';
        html +="</div>";
    } 
    if(row.contract_prov){
        html +='<div class ="fund-cont"><span class="availContractCal prov" tabindex="0"><span class="aicon fa fa-file-signature"> </span><span class="anum">'+row.contract_prov+"</span></span>";
        if(row.amount_left_prov) html +='<span class="amount">'+moneyDisplay(row.amount_left_prov)+'</span>';
        html +="</div>";
    } 
    html+= '</div>';
    html +='</div>';
   
    html += "</div>";// end card-body
    html += "</div>";// end card

    return html;

}