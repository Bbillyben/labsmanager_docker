function update_organization_chart(){
    var urlOC = Urls['api:employee-organization-chart']()
    console.log("[update_organization_chart] at url :"+urlOC)
    $.ajax({
        url: urlOC,
        type: 'GET',
        contentType: 'application/json',
        dataType: 'json',
        accepts: {
            json: 'application/json',
        },
        success: function(response){build_organization_chart(response);},
        error: function(xhr) {
            // TODO: Handle error
            console.error(`Error in update_organization_chart at '${urlOC}'`);
        }
    });
}

// https://github.com/nhmvienna/bs5treeview/tree/main
function build_organization_chart(datas){
    console.log("build_organization_chart");
    console.log(datas);
    tree =[];
    //datas.forEach((employee) => build_employee_chart(employee, tree) );
    datas.sort(comparteSubordinate)
    for(var index in datas){
        build_employee_chart(datas[index], tree);
    }
   
    $('#chart-container').bstreeview({ 
        data: tree,
        indent: 3,
    });
}

function build_employee_chart(employee, c_tree){
    var n_tree={};
    n_tree.text=employeeFormatter(employee); //employee.first_name + ' ' + employee.last_name;

    //n_tree.icon='fa fa-user';
    n_tree.expanded = true;
    if(employee.status){
        n_tree.text+="<span class='org-chart-status'>"+fullStatusFormatter(employee.status)+'</span>';
    }
    // pour le status
    if(employee.subordinate_count>0){
        n_tree.text += "<sup class='org-chart-count'>"+employee.subordinate_count+"</sup>" ;
        employee.subordinate.sort(comparteSubordinate);
        n_tree.nodes=[];
        for(var index in employee.subordinate){
            build_employee_chart(employee.subordinate[index], n_tree.nodes)
        }
    }

    c_tree.push(n_tree)


}
function comparteSubordinate(a, b){
    if(a.subordinate_count > b.subordinate_count)return -1;
    if(a.subordinate_count < b.subordinate_count)return 1;
    return 0;
}