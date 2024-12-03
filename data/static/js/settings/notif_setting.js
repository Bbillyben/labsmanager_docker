function init_notif_admin_btn(){
    $(".btn-launcher").each(function(){  init_btn_launcher(this); })
}
function init_btn_launcher(btn){
    $(btn).off('click');
    $(btn).on("click", function(){
        var url = $(btn).data("url");
        csrftoken = getCookie('csrftoken');
        $.ajax({
            type:"POST",
            url: url,
            data:{
                    csrfmiddlewaretoken: csrftoken,
            },
            success: function( data )
            {
                // console.log("Success")
                // console.log(data)
                message= data.response
                showMessage(message,{
                    'style':'success',
                })
                
            },
            error: function( err )
            {
                // console.log("Error Send Test Mail :"+err);
                // btn.addClass('btn-warning').removeClass('btn-primary').removeClass('btn-success');
                if(undefined != err.responseJSON){
                    errMess = err.responseJSON.message;
                }else{
                    errMess = "NOTIF ERROR";
                }
                showMessage("Error notification :"+errMess,{
                    'style':'danger',
                })
            },
            complete:function(arg)
            {
                // update pending notification table
                table=$("#cardtable_container_PendingNotifications").find('table');
                $(table).bootstrapTable('refresh');
                
            }
        })

    })
}