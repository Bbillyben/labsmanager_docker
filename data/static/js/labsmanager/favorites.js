function initFavorites(){
    // console.log("initFavorites")
    $('.favorite').each(function(){
        fType=$(this).data('type')
        fPk=$(this).data('pk')
        
        var csrftoken = getCookie('csrftoken');
        $.ajax({
            beforeSend: function(xhr) {
                xhr.setRequestHeader('X-CSRFToken', csrftoken);
            },
            context: this,
            url : Urls['favorite_star'](),
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
            fType=$(this).data('type')
            fPk=$(this).data('pk')
            var csrftoken = getCookie('csrftoken');
            $.ajax({
                beforeSend: function(xhr) {
                    xhr.setRequestHeader('X-CSRFToken', csrftoken);
                },
                context: this,
                url : Urls['favorite_toggle'](),
                type : 'POST',
                data : {
                    type:fType,
                    pk:fPk, 
                    csrfmiddlewaretoken:csrftoken,
                },
                success : function(response, textStatus, jqXhr) {
                    
                    $(this).html(response)
                    loadInTemplate($('#favorites'),Urls['nav_favorites']());
                },
                error : function(jqXHR, textStatus, errorThrown) {
                    // log the error to the console
                    console.log("The following error occured: " + textStatus, errorThrown);
                },
            });


        })
        
    })
}