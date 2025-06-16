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
    $("#employee_highlight").on("input", highlight_employee)
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
        //console.log(JSON.stringify(tree[sup]))
        $('#chart-container').append("<div class='row'><div class='org-chart-cont' id='chart_cont_"+sup+"'></div></div>")
        $('#chart-container #chart_cont_'+sup).orgchart({ 
            data: tree[sup],
            nodeContent: "title",
            pan:true,
            //zoom:true,
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
    n_tree.className=(employee.active?"active":"inactive");
    // pour le status
    if(employee.subordinate.length>0){
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

function highlight_employee(e){
    
    $(".title").removeClass("highlighted");
    $(".title").removeClass("highlighted_hier");
    $(".title").removeClass("highlighted_bos");
    $(".title").removeClass("greyed");
    var search = e.target.value.trim();

    console.log("Highlight "+ search );
    if (!search) return;
    $(".title").addClass("greyed");
    var re = new RegExp(search, "i");
    

    $(".title").each(function() {
        // On prend le texte affiché (par exemple celui du <a> dans .title)
        var txt = $(this).text();
        if (re.test(txt)) {
            $(this).addClass("highlighted").removeClass("greyed");
        }
    });

     $(".title.highlighted").each(function() {
        console.log("find sub for : "+$(this).text());
        $(this).parent().next(".nodes").find(".title:not(.highlighted)").each(function(sub){
                    console.log("sub : "+$(this).text());
                    if(!$(this).hasClass("highlighted_bos"))$(this).addClass("highlighted_hier").removeClass("greyed");
            });
         $(this).parent().parent().parent().parent().find(".node").first().find(".title").first().each(function(sub){
                    console.log("super : "+$(this).text());
                    if(!$(this).hasClass("highlighted"))$(this).addClass("highlighted_bos").removeClass("greyed");
            });
    });

    
}