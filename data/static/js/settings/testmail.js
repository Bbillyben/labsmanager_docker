function initTestMailBtn(el, el2){
    // console.log("Element text"+JSON.stringify(el));
    $(el).on('click', callTestMail)
    $(el2).on('click', callOpenTestMail)
}

function callTestMail(el){
    // console.log("callTestMail"+this);
    var btn=$(this);
    lockLoadBtn(btn)
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
            setBtnBack(btn)
            
        }
    })
    
}

function callOpenTestMail(el){
    // console.log("callTestMail"+this);
    var btn=$(this);
    lockLoadBtn(btn)

    csrftoken = getCookie('csrftoken');
    $.ajax({
        type:"POST",
        url: Urls['get_test_mail'](),
        data:{
                user:user_id,
                csrfmiddlewaretoken: csrftoken,
        },
        success: function( data )
        {
            btn.addClass('btn-success').removeClass('btn-primary').removeClass('btn-warning');
            showMessage("Ok",{
                'style':'success',
            })
            var w = window.open("", "Test Mail");
            w.document.title = "LabsManager Test Mail"
            w.document.
            w.document.body.style.background = "#FFFFFF";
            w.document.body.innerHTML=data; 
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
            setBtnBack(btn)
            
        }
    })
    
}

function lockLoadBtn(btn){
    btn.prop('disabled', true);
    btn.find(".initial").hide();
    btn.find(".spinner").show();
}
function setBtnBack(btn){
    btn.prop('disabled', false);
    btn.find(".initial").show();
    btn.find(".spinner").hide();
    setTimeout(
        function() {
            btn.addClass('btn-primary').removeClass('btn-warning').removeClass('btn-success');
        }, 3000);
}