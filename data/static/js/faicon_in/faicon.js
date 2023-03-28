$( document ).ready(function() {
    var icon_field = null;
    var style = [];
    $( '<div id="faicon-modal-cont"></div>' ).appendTo( "body" );
    $( "#faicon-modal-cont" ).load( "/faicon/render_icon_list_modal/" ,function() {

        function close_over() {
            $('.faicon-screen').removeClass('show');
            $('body').removeClass('faicon-active');
        }

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

            // add click handler to overpass svg transformation from FA
            $('.faicon-screen .close').on('click', function(){close_over();})
            // $('#faicon-style-select').hide()
            $('.faicon-header .search').hide()
            // $('.faicon-header .search').attr('type', 'search');


        })

        $('.faicon-delete').on('click', function(){
            $(this).siblings('input').val('');
            $(this).hide();
            $(this).siblings('.icon').html('');
            $(this).siblings('[rel="faicon-add"]').show();
        })

        

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
            console.log("faicon-modal-cont - do_search")
            var style = $('#faicon-style-select').val();
            faiconList.filter(function(item) {
                return (item.values().style == style || !style);
            });
        }
        $('#faicon-style-select').change(function(){
            do_search();
        });

    });

});