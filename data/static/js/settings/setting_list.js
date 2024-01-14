function settingListActionFormatter(value, row, index, field){
    actions = "<span class='icon-left-cell btn-group'>";
    if(this.urladmin != undefined && this.urladmin!="" && this.urladmin!='None'){
        actions += "<a href='"+Urls[this.urladmin](row.pk)+"'><button class='icon admin_btn btn btn-primary'><i type = 'button' class='fas fa-shield-halved'></i></button></a>";
    }
    if(this.urlupdate != undefined && this.urlupdate!="" && this.urlupdate!='None'){
        actions += "<button class='icon edit btn btn-success' data-form-url='"+Urls[this.urlupdate](row.pk)+"' ><i type = 'button' class='fas fa-edit'></i></button>";
    }
    
    if(this.urldelete != undefined && this.urldelete!="" && this.urldelete!='None'){
        actions += "<button class='icon delete btn btn-danger' data-form-url='" + Urls[this.urldelete](row.pk) + "' ><i type = 'button' class='fas fa-trash'></i></button>";
    }
    actions += "</span>"
    return actions;
}


(function($) {
    $.lab_settinglist = function(element, options) {

        var defaults = {
            table:{
                search: false,
                showColumns: false,
                disablePagination: true,
                playCallbackOnLoad:true,
            },
        };
        var table;
        var plugin = this;
        var card = element;
        plugin.settings = {}

        plugin.init = function() {
            // console.log("lab_settinglist - INIT")
            plugin.settings = $.extend(true, {}, defaults, options);

            // table => bootstrap table
            table=$(card).find('table');
            plugin.settings.table.callback=plugin.updateSettingCardBtn;
            $(table).labTable(plugin.settings['table']);

            // btn add setting
            $(card).find('.setting_add').each(function(){

                $(this).labModalForm({
                        formURL: $(this).data("form-url"),
                        modal_title:"Add",
                        addModalFormFunction:function(){
                            console.log("refresh from add modal")
                            console.log(table)
                            $(table).bootstrapTable('refresh');
                        },
                    }   
                )
            })
        };

        plugin.updateSettingCardBtn=function(){
            // console.log("[updateSettingCardBtn]")
            $(table).find('.edit').each(
                function () {
                    $(this).labModalForm({
                        formURL:  $(this).data("form-url"),
                        modal_title:"Edit",
                        addModalFormFunction: function(){
                            $(table).bootstrapTable('refresh');
                            plugin.updateSettingCardBtn(table);
                        },
                    })
                }
            )
        }

        plugin.init();
    };

    $.fn.lab_settinglist = function(options) {

        return this.each(function() {
            if (undefined == $(this).data('lab_settinglist')) {
                var plugin = new $.lab_settinglist(this, options);
                $(this).data('lab_settinglist', plugin);
            }

        });

    }

})(jQuery); 
