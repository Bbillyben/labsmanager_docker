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