
function consumptionFormatter(value, row, index, field){
    if(isNaN(value))return '-'
    pr=row.ratio
    tr=row.time_ratio
    response ='<div class="d-flex flex-wrap">'
    response += quotityDisplay(value);

    if(!isNaN(pr) && !isNaN(tr)){
        response+= '<span class="flex" style="flex-grow: 1;"></span>'
        if(pr > tr ){
            response+= ' <i class="fa-solid fa-arrows-up-to-line text-warning"></i>'
        }else{
            response+= ' <i class="fa-solid fa-arrows-down-to-line text-danger"></i>'
        }
        
    }
    response +="</div>"


    return response

}