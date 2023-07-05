function initSubscription(){
    // console.log("initFavorites")
    $('.subscription').each(function(){
        fType=$(this).data('type')
        fPk=$(this).data('pk')
        
        var csrftoken = getCookie('csrftoken');
        $.ajax({
            beforeSend: function(xhr) {
                xhr.setRequestHeader('X-CSRFToken', csrftoken);
            },
            context: this,
            url : Urls['subscription_bell'](),
            type : 'POST',
            data : {
                type:fType,
                pk:fPk, 
                csrfmiddlewaretoken:csrftoken,
            },
            success : function(response, textStatus, jqXhr) {
                $(this).html(response)
            },
            error : function(jqXHR, textStatus, errorThrown) {
                // log the error to the console
                console.log("The following error occured: " + textStatus, errorThrown);
            },
        });


        
        $(this).on('click', function(){
            console.log("subs licked");
            fType=$(this).data('type')
            fPk=$(this).data('pk')
            var csrftoken = getCookie('csrftoken');
            $.ajax({
                beforeSend: function(xhr) {
                    xhr.setRequestHeader('X-CSRFToken', csrftoken);
                },
                context: this,
                url : Urls['subscription_toggle'](),
                type : 'POST',
                data : {
                    type:fType,
                    pk:fPk, 
                    csrfmiddlewaretoken:csrftoken,
                },
                success : function(response, textStatus, jqXhr) {
                    
                    $(this).html(response)
                },
                error : function(jqXHR, textStatus, errorThrown) {
                    // log the error to the console
                    console.log("The following error occured: " + textStatus, errorThrown);
                },
            });


        })
        
    })
}

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
        
    }
    return response
}

function subObjectUrlFormatter(value, row, index, field){
    response = "";
    response += "<a href='"+row.object_url+"'>"+value+"</a>";
    return response
}