var user_id = 0;
var project_id = 0;

function initFundFinder(user_idA){
    user_id=user_idA;
    var filters = loadTableFilters('funditem');
    var filterOption={
        download:true,
    }
    var options={
        queryParams: filters,
        name:'funditem',
        post_body_callback:updateFundFinderTagble,
        
    }
    setupFilterList('funditem', $('#fund_main_table'), '#filter-list-funditem',filterOption);
    $('#fund_main_table').labTable(options);

}

function updateFundFinderTagble(){
    options={
        html:true,
        customClass:'availContTooltip',
    }

    var tooltipTriggerList = [].slice.call(document.querySelectorAll('.availContract[data-bs-toggle="tooltip"]'))
    var tooltipList = tooltipTriggerList.map(function (tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl, options)
    })

}