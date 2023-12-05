function update_organization_chart(){
    var urlOC = Urls['api:employee-organization-chart']()
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
//https://github.com/dabeng/OrgChart/tree/master

function build_organization_chart(datas){
    tree =[];
    //datas.forEach((employee) => build_employee_chart(employee, tree) );
    datas.sort(comparteSubordinate)
    for(var index in datas){
        build_employee_chart(datas[index], tree);
    }
    for (sup in tree){
        console.log(JSON.stringify(tree[sup]))
        $('#chart-container').append("<div class='row'><div id='chart_cont_"+sup+"'></div></div>")
        $('#chart-container #chart_cont_'+sup).orgchart({ 
            data: tree[sup],
            nodeContent: "title",
            pan:true,
            verticalLevel:3,

            
        });

    }
}
function build_employee_chart(employee, c_tree){
    var n_tree={};
    n_tree.name=employeeFormatter(employee); //employee.first_name + ' ' + employee.last_name;

    if(employee.status){
        n_tree.title="<span class='org-chart-status'>"+statusFormatter(employee.status)+'</span>';
    }else{
        n_tree.title=""
    }
    // pour le status
    if(employee.subordinate_count>0){
        employee.subordinate.sort(comparteSubordinate);
        n_tree.children=[];
        for(var index in employee.subordinate){
            build_employee_chart(employee.subordinate[index], n_tree.children)
        }
    }

    c_tree.push(n_tree)


}

// For legacy purpose : View of organisation by a tree
// https://github.com/nhmvienna/bs5treeview/tree/main
// function build_organization_chart(datas){
//     tree =[];
//     //datas.forEach((employee) => build_employee_chart(employee, tree) );
//     datas.sort(comparteSubordinate)
//     for(var index in datas){
//         build_employee_chart(datas[index], tree);
//     }
//     for (sup in tree){
//         $('#chart-container').append("<div class='col'><div id='chart_cont_"+sup+"'></div></div>")
//         $('#chart-container #chart_cont_'+sup).bstreeview({ 
//             data: [tree[sup]],
//             indent: 2,
//             openNodeLinkOnNewTab:false,
//         });

//     }
// }

// function build_employee_chart(employee, c_tree){
//     var n_tree={};
//     n_tree.text=employeeFormatter(employee); //employee.first_name + ' ' + employee.last_name;

//     //n_tree.icon='fa fa-user';
//     n_tree.expanded = true;
//     if(employee.status){
//         n_tree.text+="<span class='org-chart-status'>"+statusFormatter(employee.status)+'</span>';
//     }
//     // pour le status
//     if(employee.subordinate_count>0){
//         n_tree.text += "<sup class='org-chart-count'>"+employee.subordinate_count+"</sup>" ;
//         employee.subordinate.sort(comparteSubordinate);
//         n_tree.nodes=[];
//         for(var index in employee.subordinate){
//             build_employee_chart(employee.subordinate[index], n_tree.nodes)
//         }
//     }

//     c_tree.push(n_tree)


// }
function comparteSubordinate(a, b){
    if(a.subordinate_count > b.subordinate_count)return -1;
    if(a.subordinate_count < b.subordinate_count)return 1;
    return 0;
}