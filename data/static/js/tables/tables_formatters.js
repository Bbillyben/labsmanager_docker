/*  --------------------------------------------------
                  Basic Tables cell formatter         
------------------------------------------------------- */

// --------------------------------------------------------------------------------Sytle
function styleAlignMiddle(value, row, index, field){
    response={
    //classes: 'text-nowrap another-class',
        css: {"text-align": "center"}
    }
      return response;
}
function simpleStyle(value, row, index, field){
    response="";
    switch(field) {
        case 'active':
        case 'team_leader':
        case 'team_participant':
        case 'is_active':
            response={
                //classes: 'text-nowrap another-class',
                css: {"text-align": "center"}
                }
          break;
        default:
          // code block
      }

      return response;
}

// ------------------------------------------------------------ Generic  Formatter 
function basicBoolean(value, row, index, field){
    response = (value ? '<img src="/static/admin/img/icon-yes.svg" alt="True">' : '<img src="/static/admin/img/icon-no.svg" alt="False">');
    response += '<span style="display:none">'+ value+"</span>";
    return response
}


function colorFormatter(value, row, index, field){
    response = "<span class='color-dot'style=' background-color:"+value+";'></span>"
    return response;
}   
function iconFormatter(value, row, index, field){
    response = "<i class='"+value.style+" fa-"+value.icon+"'></i>"
    return response;
}   
function m2mBaseFormatter(value, row, index, field){
    response=value.map(function(elem){
        return elem.name;
    }).join(", ");

    return response
}
function treeNameFormatter(value, row, index, field){
    response = ""
    for(i=0; i<row.ancestors_count; i++){
        if(i==0){response +="┝";}else{response +="┅";}
        response +="━";
        if(i==row.ancestors_count-1)response +=" "
    }
    response+=value
    return response
}

function simpleFormatter(value, row, index, field){
    //console.log('simpleFormatter : '+JSON.stringify(value)+" - row : "+JSON.stringify(row) + "  - index :"+index+ " - fiels :"+field);
    response="";
    switch(field) {
        case 'is_active':
            response=(value ? '<img src="/static/admin/img/icon-yes.svg" alt="True">' : '<img src="/static/admin/img/icon-no.svg" alt="False">');
            break;
        default:
          // code block
      }

      return response;
}

// ------------------------------------------------------------ Generic  Formatter date

function dueDatePassed(value, row, index, field){
    curr=new Date();
    valDate=Date.parse(value);
    //console.log('date test :'+(curr.getTime()>valDate));
    
    if(curr.getTime()>valDate){
        return '<span class="alert-danger">'+value+'</span>';
    }
    return value
}
function baseDateFormatter(value, row, index, field){
    if(value == null || value =="")return value
    d=new Date(value)
    if (d == "Invalid Date" )return value;
    return d.toLocaleDateString()
}

function calDateFormatter(value, row, index, field){
    if(value == null || value =="")return value
    d=new Date(value)
    if (d == "Invalid Date" )return value;
    return d.toLocaleDateString() + " - "+ row[field+"_period_di"]
}

// ------------------------------------------------------------ Generic  Formatter Qutotity


function quotityFormatter(value, row, index, field){
    if(isNaN(value))return '-'
    return quotityDisplay(value);
}

function quotityAlertFormatter(value, row, index, field){
    if( value == null || isNaN(value) ){
        return "-";
    }
    val = quotityDisplay(value)
    if(value > 1){
        return "<div class='warning-quotity'>"+val+"</div>";
    }else{
        return "<div class=''>"+val+"</div>";
    }
}
// ------------------------------------------------------------ Generic  Formatter Money
function moneyFormatter(value, row, index, field){
    return moneyDisplay(value);
}
function moneyFormatter_alert(value, row, index, field){
    response = '<span class="'+(value < 0 ? "text-danger":'')+'">';
    response+=moneyDisplay(value);
    response+='</span>';
    return response;
}


function moneyFocusFormatter(value, row, index, field){
    //console.log("[moneyFocusFormatter] custom data :"+this.custom_param)
    str = moneyFormatter(value, row, index, field)
    focusItem = row[this.custom_param]
    if(focusItem != undefined && focusItem != value){
        str += "<small> ("+moneyDisplay(focusItem)+") </small>"
    }
    return str

}


// ------------------------------------------------------------ Employee  Formatter
function userFormatter(value, row, index, field){
    if(row['has_perm'] == true ){
      response =  '<span class="icon-right-cell"><a href="/staff/employee/'+row.pk+'" title="/staff/employee/'+row.ipkd+'/"> '+row.first_name+" "+row.last_name+'</a></span>';
    }else{
      response =  '<span class="icon-right-cell">'+row.first_name+" "+row.last_name+'</span>';
    }
    
    response += '<span class="icon-left-cell">';
  if(row.is_team_leader){
    response+='<span type="button" class="icon-spaced show_teamlead" data-emp_pk="'+row.pk+'" ><i class="fas fa-crown icon-spaced" style="color: coral" title="team leader"></i></span>';
  }
  if(row.is_team_mate){
    response+='<span type="button" class="icon-spaced show_teamlead" data-emp_pk="'+row.pk+'" ><i class="fas fa-user-friends" style="color: cadetblue" title="team mate"></i></span>';
  }

    if(row.has_subordinate || row.superior.length>0){
        response+='<span type="button"  class="icon-spaced show_orgchart" data-emp_pk="'+row.pk+'" ><i  class="fas fa-sitemap" style="color: var(--primary-color)" title="subordinate"></i></span>';
    }

  response += '</span>';

    return response;
}

function employeeFormatter(value, row, index, field){

    if(!isIterable(value)){
        value=[{"employee":value}];
    }
    can_see = USER_PERMS.includes('staff.view_employee')
    response = "";
    for (const item of value) {
        // console.log("item :"+JSON.stringify(item));
            if("employee" in item && item.employee!=null){
                if(can_see || item.employee.pk == USER_EMPLOYEE || (row && row.has_perm == true)){
                    tm ="<a href='/staff/employee/"+item.employee.pk+"'>"+item.employee.user_name+"</a>";
                }else{
                    tm =item.employee.user_name;
                }
                response+= (response.length > 1 ? ', ' : '') + tm;
            }else{
                response +="-"
            }
            
      }
      return response;
}

function teamMateFormatter(value, row, index, field){
    
    if(!isIterable(value)){
        value=[{"employee":value, "is_active":value.is_active}];
    }
    response = "";
    can_see = USER_PERMS.includes('staff.view_employee') ;
    for (const item of value) {
        if(can_see){
            tm ="<a href='/staff/employee/"+item.employee.pk+"'>"+item.employee.user_name+"</a>";
        }else{
            tm =item.employee.user_name;
        }
        if(!item.is_active)tm +='<sup><img src="/static/admin/img/icon-no.svg" alt="False" style="width:1em;"></img></sup>'
        response+= (response.length > 1 ? ', ' : '') + tm;
      }
      return response;
}
function organisationEmployeeFormatter(value, row, index, field){
    response = "";
    can_see = USER_PERMS.includes('staff.view_employee')
    active = !(!value.is_active || (row.is_active != undefined && !row.is_active));
    response+='<span class="'+(active?"active":"inactive")+'">';
    if(can_see){
        response +="<a href='/staff/employee/"+value.pk+"'>"+value.user_name+"</a>";
    }else{
        response +=value.user_name;
    }
    response+='</span>';
    
    return response;

}
function incommingEmployeeFormatter(value, row, index, field){
    response = "<span>";
    can_see = USER_PERMS.includes('staff.view_employee')
    // active = !(!value.is_active || (row.is_active != undefined && !row.is_active));
    // response+='<span class="'+(active?"active":"inactive")+'">';
    if(can_see){
        response +="<a href='/staff/employee/"+row.pk+"'>"+row.user_name+"</a>";
    }else{
        response +=row.user_name;
    }
    response+='</span>';
    
    return response;
}
function ParticipantFormatter(value, row, index, field){

    if(!isIterable(value)){
        value=[{"employee":value}];
    }
    response = "";
    value = value.sort(leaderSorter);
    for (const item of value) {
        //console.log("item :"+JSON.stringify(item));
        if (item.employee.is_active == true){

            tm ="<a href='/staff/employee/"+item.employee.pk+"'>"+item.employee.user_name;
            if(item.status == "l"){
                tm+= '<sup><i class="fas fa-crown icon-spaced" style="color: coral" title="team leader"></i></sup>';
            }else if(item.status == "cl"){
                tm+= '<sup><i class="fas fa-crown icon-spaced" style="color: cadetblue" title="team leader"></i></sup>';
            }
            tm+="</a>";
            response+= (response.length > 1 ? ', ' : '') + tm;
        }
      }
      return response;
}
// ------------------------------------------------------------ Generic  Formatter 
function ParticipantStatusFormatter(value, row, index, field){
    response = "<span>"
    response+="<i class='icon-spaced  fa fa-flask "+(row.project.status? "icon-green":"icon-red")+"' title='Project active'></i>"
    response+="<i class='icon-spaced fa fa-user "+(row.is_active? "icon-green":"icon-red")+"' title='participant active'></i>"
    return response
}

function leaveEmployeeFormatter(value, row, index, field){
    response =  '<a href="'+Urls['employee'](row.employee_pk)+'" title="/'+row.employee_pk+'/"> '+value+'</a>';
    return response;
}

function employeeSuperiorsFormatter(value, row, index, field){
    if(!isIterable(value)){
        value=[{"employee":value}];
    }
    can_see = USER_PERMS.includes('staff.view_employee')
    response = "";
    for (const item of value) {
        // console.log("item :"+JSON.stringify(item));ponse +=row.user_name;
            if("employee" in item && item.employee!=null){
                if(can_see) {
                    tm ="<a href='/staff/employee/"+item.employee_superior.pk+"'>"+item.employee_superior.user_name+"</a>";
                } else{
                    tm =item.employee_superior.user_name;
                }
                response+= (response.length > 1 ? ', ' : '') + tm;
            }else{
                response +="-"
            }
            
      }
      return response;
}
// ------------------------------------------------------------ Employee Additional Info Formatter
function statusFormatter(value, row, index, field){
    response = '';
    //console.log('statusFormatter : '+JSON.stringify(value)+" - row : "+JSON.stringify(row) + "  - index :"+index+ " - fiels :"+field+"  # allow :"+this.allow);
    for (const item of value) {
      if (item.is_active){
        response+= (response.length > 1 ? ', ' : '') + item.type.shortname
      }
    }
  
    return response;
  }
function fullStatusFormatter(value, row, index, field){
    response = '';
    //console.log('statusFormatter : '+JSON.stringify(value)+" - row : "+JSON.stringify(row) + "  - index :"+index+ " - fiels :"+field+"  # allow :"+this.allow);
    for (const item of value) {
      if (item.is_active){
        response+= (response.length > 1 ? ', ' : '') + item.type.name
      }
    }
  
    return response;
  }

function infoFormatter(value, row, index, field){
    response = '<ul>';
    //console.log('infoFormatter : '+JSON.stringify(value)); //+" - row : "+JSON.stringify(row) + "  - index :"+index+ " - fiels :"+field+"  # allow :"+this.allow);
    for (const item of value) {
      response +="<li>"+item.info.name + " : "+item.value+"</li>"
    }
    response +="</ul>"
    return response;
  }

// ------------------------------------------------------------ Institution  Formatter
function institution_formatter(value, row, index, field){
    responseI = "";
    can_see = USER_PERMS.includes('common.display_infos');
    if(can_see){
        responseI ="<a href='"+Urls['orga_single']("project", "institution", row.pk)+"'>"+value+"</a>";
    }else{
        responseI =value;
    }
    return responseI
}
function InstitutionParticipantFormatter(value, row, index, field){
    if(!isIterable(value)){
        value=[{"institution":value}];
    }
    response = "";
    value = value.sort(leaderSorter);
    for (const item of value) {
            tm = institution_formatter(item.institution.short_name, item.institution);
            if(item.status == "c"){
                tm+= '<sup><i class="fas fa-star icon-spaced" style="color: coral" title="leader"></i></sup>';
            }
            //tm+="</a>";
            response+= (response.length > 1 ? ', ' : '') + tm;
      }
      return response;


}

// ------------------------------------------------------------ Project  Formatter
function ProjectFormatter(value, row, index, field){
    // console.log("ProjectFormatter :"+JSON.stringify(value))
    if(!isIterable(value)){
        value=[{"project":value}];
    }
    response = "";
    for (const item of value) {
        // console.log("item :"+JSON.stringify(item));

            tm ="<a href='/project/"+item.project.pk+"'>"+item.project.name;
            tm+="</a>";
            response+= (response.length > 1 ? ', ' : '') + tm;
      }
      return response;
}
function ProjectFormatterList(value, row, index, field){
    response =  '<span class="icon-right-cell"><a href="'+Urls['project_single'](row.pk)+'" title="/'+row.ipkd+'/"> '+value+'</a>';
    return response;
}

function projectsFormatter(value, row, index, field){
    //console.log('contractsFormatter : '+JSON.stringify(value)+" - row : "+JSON.stringify(row) + "  - index :"+index+ " - fiels :"+field+"  # allow :"+this.allow);
    response = '<ul>';
    for (const item of value) {
      if (item.project.status == true){
        response+= '<li>'+item.project.name+ " / "+item.status+" ("+quotityDisplay(item.quotity)+")"+"</li>";
      }
    }
    response += '</ul>';
  
    return  response;
  }
  

function projectFormatterDirect(value, row, index, field){
    // console.log(value)
    // console.log(row)
    response = '<a href="/project/'+value.pk+'" >'+value.name+"</a>";
    return response;
}


// ------------------------------------------------------------ Fund  Formatter
function SingleFundFormatter(value, row, index, field){
    
    response = "";
    response +=value.funder.short_name;
    response+=" - "+value.institution.short_name;
    response+=" ("+value.ref;
    response+=" - "+moneyDisplay(value.amount)+")"
    
      return response;
}
function FundFormatter(value, row, index, field){
    

    if(!isIterable(value)){
        value=[value];
    }
    response = "<ul>";
    for (const item of value) {
        response +="<li>"+item.funder.short_name;
        response+=" - "+item.institution.short_name;
        response+=" ("+item.ref;
        response+=" - "+moneyDisplay(item.amount)+")"
        response+="</li>";
      }
      response += "</ul>";
      return response;
}

function FocusItemFormatter(value, row, index, field){
    // console.log("[FocusItemFormatter]")
    // console.log(JSON.stringify(row))
    response = value;
    if(row.type != undefined){
        type=row.type;
    }else if(row.cost_type != undefined){
        type=row.cost_type;
    }
    if(type!=undefined && !type.in_focus){
        response+='<sup class="out-focus"><small><i class="fas fa-eye-slash" title="Out of focus"></i></small></sup>'
    }

    return response;
    
}
function availableFundItem_alert(value, row, index, field){
    response = moneyFormatter_alert(value, row, index, field);
    if(row.contract.length > 0){
        var cc = "";
        for (var i = 0; i < row.contract.length; i++) {
            if(cc.length>1)cc+="<br>";
            cc+=row.contract[i].employee.user_name+' - '
            if(row.contract[i].quotity)cc+=quotityFormatter(row.contract[i].quotity)
            if(row.contract[i].contract_type)cc+=" - "+row.contract[i].contract_type
            if(row.contract[i].end_date)cc+=" - "+row.contract[i].end_date;
          }
        response+='<span class="availContract" tabindex="0" data-bs-toggle="tooltip" data-bs-placement="top" title="'+cc+'"><span class="aicon fa fa-file-signature"> </span><span class="anum">'+row.contract.length+"</span></span>";
    }
    return response;
}

// ------------------------------------------------------------ Team  Formatter
function TeamFormatter(value, row, index, field){
    if(row['has_perm'] == true ){
        response =   '<span class="icon-right-cell"><a href="'+Urls['team_single'](row.pk)+'" title="/'+row.ipkd+'/"> '+value+'</a></span>';
      }else{
        response ='<span class="icon-right-cell"> '+value+'</span>';
      }
    
    return response;
}

// ------------------------------------------------------------ Contract  Formatter
function ContractProjectFormatter(value, row, index, field){
    // console.log("ContractProjectFormatter :"+JSON.stringify(row.status))
    response = '<i class="fa-solid fa-circle-check contractlist ';
    response+= row.status;
    response+= '"';
    response+='title="'+(row.status=="effe"?"effective":"provisionnal")+'"';
    response+='></i>'+" ";

    response += ProjectFormatter(value, row, index, field);
    return response;
}
function ContractEmployeeFormatter(value, row, index, field){
    // console.log("ContractProjectFormatter :"+JSON.stringify(row.status))
    response = '<i class="fa-solid fa-circle-check contractlist ';
    response+= row.status;
    response+= '"';
    response+='title="'+(row.status=="effe"?"effective":"provisionnal")+'"';
    response+='></i>'+" ";

    response += employeeFormatter(value, row, index, field);
    return response;
}
function contractsFormatter(value, row, index, field){
    //console.log('contractsFormatter : '+JSON.stringify(value)+" - row : "+JSON.stringify(row) + "  - index :"+index+ " - fiels :"+field+"  # allow :"+this.allow);
    response = '<ul>';
    var d = new Date();
    for (var item of value) {
      if (item.end_date == null || new Date(item.end_date) > d){
        response+= '<li>'+item.fund.institution.short_name+ " / "+item.fund.project.name+" - "+item.fund.funder.short_name+" ("+quotityDisplay(item.quotity)+" - "+item.start_date+")"+"</li>";
      }
    }
    response += '</ul>';
  
    return  response;
  }
// ------------------------------------------------------------ Subscription  Formatter
function subsTypeIconFormatter(value, row, index, field){
    response = "";
    switch (row.content_type.model) {
        case 'employee':
            response += '<i class="icon icon-badge icon-inline fas fa-user" title="employee"></i>';
            break;
        case 'project':
            response += '<i class="icon icon-badge icon-inline fas fa-flask" title="project"></i>';
            break;
        case 'team':
            response += '<i class="icon icon-badge icon-inline fas fa-people-group" title="team"></i>';
            break;
        case 'institution':
            response += '<i class="icon icon-badge icon-inline fas fa-landmark" title="Institution"></i>';
            break;
        case 'fund_institution':
            response += '<i class="icon icon-badge icon-inline fas fa-piggy-bank" title="Institution"></i>';
            break;
        
    }
    return response
}

function subObjectUrlFormatter(value, row, index, field){
    response = "";
    response += "<a href='"+row.object_url+"'>"+value+"</a>";
    return response
}
// ------------------------------------------------------------ Organization  Formatter

function organization_formatter(value, row, index, field){
    responseI = "";
    can_see = USER_PERMS.includes('common.display_infos');
    if(can_see){
        responseI ="<a href='"+Urls['orga_single'](this.app, this.model, row.pk)+"'>"+value+"</a>";
    }else{
        responseI =value;
    }
    return responseI
}
function institution_project_formatter(value, row, index, field){
    responseI = "";
    can_see = USER_PERMS.includes('common.display_infos');
    if(can_see){
        responseI ="<a href='"+Urls['orga_single']('project', 'institution', row.institution.pk)+"'>"+value+"</a>";
    }else{
        responseI =value;
    }
    return responseI
}
function institution_fund_formatter(value, row, index, field){
    responseI = "";
    can_see = USER_PERMS.includes('common.display_infos');
    if(can_see){
        responseI ="<a href='"+Urls['orga_single']('project', 'institution', row.fund.institution.pk)+"'>"+value+"</a>";
    }else{
        responseI =value;
    }
    return responseI
}

function funder_formatter(value, row, index, field){
    responseI = "";
    can_see = USER_PERMS.includes('common.display_infos');
    if(can_see){
        responseI ="<a href='"+Urls['orga_single']('fund', 'fund_institution', row.funder.pk)+"'>"+value+"</a>";
    }else{
        responseI =value;
    }
    return responseI
}
function contract_funder_formatter(value, row, index, field){
    responseI = "";
    can_see = USER_PERMS.includes('common.display_infos');
    if(can_see){
        responseI ="<a href='"+Urls['orga_single']('fund', 'fund_institution', row.fund.funder.pk)+"'>"+value+"</a>";
    }else{
        responseI =value;
    }
    return responseI
}

function infoTypeFormatter(value, row, index, field){
    responseI = "";
    if(value.toUpperCase() !="NONE"){
        responseI =value
     }else{
        responseI ="-";
    }
    return responseI
}

function typeContactFormatter(value, row, index, field){
    response = value;
    if (row.comment && row.comment != "None"){
        response += '<span class="availComment" tabindex="0" data-bs-toggle="tooltip" data-bs-placement="right" title="'+row.comment+'"><span class="aicon fa fa-comment"> </span></span>'
    }
    return response;
}


function contactInfoFormatter(value, row, index, field){
    response = ""
    if(validateEmail(value) || row.type == "mail"){
        response+='<a href="mailto:'+value+'">'+value+'</a>';
    }else if(row.type=="tel"){
        response+='<a href="tel:'+value+'">'+value+'</a>';
        
    }else if(row.type=="link"){
        response+='<a href="'+formatAsHTMLLink(value)+'">'+value+'</a>';
    }else{
        response += value
    }
    return response;

}

// ------------------------------------------------------------ Admin Actions  Formatter

function adminActionFormatter(value, row, index, field){
    action = "<span class='icon-left-cell btn-group'>";
    if(this.isStaff=='True')action += "<a href='/admin/staff/employee/"+row.pk+"/change/'><button class='icon admin_btn btn btn-primary'><i type = 'button' class='fas fa-shield-halved'></i></button></a>"
    if(this.canChange=='True')action += "<button class='icon edit btn btn-success' data-form-url='/staff/employee/"+row.pk+"/udpate' ><i type = 'button' class='fas fa-edit'></i></button>";
    if(this.canDelete=='True') action += "<button class='icon delete btn btn-danger ' data-form-url='/staff/employee/"+row.pk+"/delete' ><i type = 'button' class='fas fa-trash'></i></button>";
    action += "</span>"
    return action;
  }
  
















