function initialiseCollapsePanel(){
    $(".panel-content.collapse").each(function(){
        id=this.id
        $("#"+id).on('show.bs.collapse hide.bs.collapse', collapseListener)
        var state = localStorage.getItem(`labsmanager-panel-collapse-${id}`) || 'show';
        if(state!="show")$("#"+id).collapse(state)
    })
}

function collapseListener(e){
    id=this.id
    type = e.type
    localStorage.setItem(`labsmanager-panel-collapse-${id}`, type);
}