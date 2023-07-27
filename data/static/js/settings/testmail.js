function initTestMailBtn(el){
    // console.log("Element text"+JSON.stringify(el));
    $(el).on('click', callTestMail)
}

function callTestMail(el){
    // console.log("callTestMail"+this);
    $(this).prop('disabled', true);

    $(this).find(".initial").hide();
    $(this).find(".spinner").show();

    var btn=$(this);

    csrftoken = getCookie('csrftoken');
    $.ajax({
        type:"POST",
        url: Urls['subs_test_mail'](),
        data:{
                user:user_id,
                csrfmiddlewaretoken: csrftoken,
        },
        success: function( data )
        {
            // console.log("Success")
            // console.log(data)
            btn.addClass('btn-success').removeClass('btn-primary').removeClass('btn-warning');
            showMessage(data.message,{
                'style':'success',
            })
            
        },
        error: function( err )
        {
            // console.log("Error Send Test Mail :"+err);
            btn.addClass('btn-warning').removeClass('btn-primary').removeClass('btn-success');
            if(undefined != err.responseJSON){
                errMess = err.responseJSON.message;
            }else{
                errMess = "SERVER ERROR";
            }
            showMessage("Error Mail Sending :"+errMess,{
                'style':'danger',
            })
        },
        complete:function(arg)
        {
            btn.prop('disabled', false);
            btn.find(".initial").show();
            btn.find(".spinner").hide();
            //btn.addClass('btn-primary').removeClass('btn-warning').removeClass('btn-success');
            
        }
    })
    
}