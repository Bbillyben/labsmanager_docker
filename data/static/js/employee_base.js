function simpleFormatter(value, row, index, field){
    //console.log('simpleFormatter : '+JSON.stringify(value)+" - row : "+JSON.stringify(row) + "  - index :"+index+ " - fiels :"+field);
    response="";
    switch(field) {
        case 'is_active':
          if(this.allow == 'True'){
            response=(value ? '<i class="fa fa-toggle-off" aria-hidden="true" style="color:green"></i>' : '<i class="fa fa-toggle-on" aria-hidden="true" style="color:red"></i>');
            response = '<span type="button" class="user_action" data-action-type="activate_user_'+(!value)+'" data-pk="'+row.pk+'">'+response+'</span>';
            response += '<span style="display:none">'+ value+"</span>";
          }else{
            response=(value ? '<img src="/static/admin/img/icon-yes.svg" alt="True">' : '<img src="/static/admin/img/icon-no.svg" alt="False">');
          }
            break;
        default:
          // code block
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

function userFormatter(value, row, index, field){
    //console.log('userFormatter : '+JSON.stringify(value)+" - row : "+JSON.stringify(row) + "  - index :"+index+ " - fiels :"+field+"  # allow :"+this.allow);
    response =  '<span class="icon-right-cell"><a href="/staff/employee/'+row.pk+'" title="/staff/employee/'+row.ipkd+'/"> '+row.first_name+" "+row.last_name+'</a>';
    response += '<span class="icon-left-cell">';
  if(row.is_team_leader){
    response+='<i class="fas fa-crown icon-spaced" style="color: coral" title="team leader"></i>'
  }
  if(row.is_team_mate){
    response+='<i class="fas fa-user-friends icon-spaced" style="color: cadetblue" title="team mate"></i>'
  }
  response += '</span>';

    return response;
}

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
function infoFormatter(value, row, index, field){
  response = '<ul>';
  console.log('statusFormatter : '+JSON.stringify(value)); //+" - row : "+JSON.stringify(row) + "  - index :"+index+ " - fiels :"+field+"  # allow :"+this.allow);
  for (const item of value) {
    response +="<li>"+item.info.name + " : "+item.value+"</li>"
  }
  response +="</ul>"
  return response;
}

function adminActionFormatter(value, row, index, field){
  action = "<span class='icon-left-cell btn-group'>";
  if(this.isStaff=='True')action += "<a href='/admin/staff/employee/"+row.pk+"/change/'><button class='icon admin_btn btn btn-primary'><i type = 'button' class='fas fa-shield-halved'></i></button></a>"
  if(this.canChange=='True')action += "<button class='icon edit_employee btn btn-success' data-form-url='/staff/employee/"+row.pk+"/udpate' ><i type = 'button' class='fas fa-edit'></i></button>";
  if(this.canDelete=='True') action += "<button class='icon delete_employee btn btn-danger ' data-form-url='/staff/employee/"+row.pk+"/delete' ><i type = 'button' class='fas fa-trash'></i></button>";
  action += "</span>"
  return action;
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



