$( document ).ready(function() {
    var icon_field = null;
    var style = [];
    $( '<div id="faicon-modal-cont"></div>' ).appendTo( ".modal-content" );
    $( "#faicon-modal-cont" ).load( "/faicon/render_icon_list_modal/" ,function() {

        function close_over() {
            $('.faicon-screen').removeClass('show');
            $('body').removeClass('faicon-active');
           
        }

        $('.modal').on("hide.bs.modal",function(e){
            $("#faicon-modal-cont").remove();
       });
       
        $('#faicon-list .list li .style').each(function(){
            var t = $(this).text();
            if (jQuery.inArray(t, style) === -1) {
                style.push(t)
                $('#faicon-style-select').append($('<option>', {
                    value: t,
                    text: t.substr(0,1).toUpperCase() + t.substr(1)
                }));
            }
        });

        $('.faicon-add').on('click', function(){
            $('body').addClass('faicon-active');
            $('.faicon-screen').addClass('show');
            icon_field = $('#'+$(this).data('id'));
        })

        $('.faicon-delete').on('click', function(){
            $(this).siblings('input').val('');
            $(this).hide();
            $(this).siblings('.icon').html('');
            $(this).siblings('[rel="faicon-add"]').show();
        })

        $('.faicon-screen').on('click','.close[data-fa-i2svg]', function(){close_over();})

        $('.faicon-screen .list li').on('click', function(){
            var i = $(this).find('svg');
            if(i==undefined){
                i = $(this).find('i');
            }
            var i_parts = $(i).attr('class').split(' ');
            var icTxt = 'style:'+$(i).data('prefix')+",icon:"+$(i).data('icon')+",prefix:"+i_parts[0].replace('svg-inline--','')
            icon_field.val(icTxt);
            icon_field.siblings('.icon')
                .html('<i class="'+$(i).data('prefix')+' '+i_parts[1]+' fa-3x"><i>');
            icon_field.siblings('[rel="faicon-add"]').hide();
            icon_field.siblings('.faicon-delete').show();
            close_over();
        })

        var options = {
            valueNames: [ 'label', 'style', 'terms'],
            page: 60,
            pagination: false,
        };

        var faiconList = new List('faicon-list', options);

        function do_search() {
            var style = $('#faicon-style-select').val();
            faiconList.filter(function(item) {
                return (item.values().style == style || !style);
            });
        }
        // $('.faicon-header #faicon-style-select').off();
        // $('.faicon-header .search').off();
        $('#faicon-style-select').change(function(){
            console.log("Change detect")
            do_search();
        });
    });

});