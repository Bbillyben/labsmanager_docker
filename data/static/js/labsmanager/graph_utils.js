function createDataSet(datas, setLabel, setXAxis, setAmount, stacked=true, makeCumulative=true){
    var datasets=[];
    var indexDict={}
    if(setLabel in datas.schema.primaryKey){
        return null;
    }
    var i=0;
    var ds;
    var seq = palette('all', Math.min(datas.data.length, 30));
  // cb-Paired cb-Pastel1
    for (var item in datas.data) {
        d=datas.data[item];
        // get the data set
        if(d[setLabel] in indexDict){
            id=indexDict[d[setLabel] ];
            ds=datasets[id];
        }else{
            indexDict[d[setLabel]]=i;
            i+=1;
            ds={
                label: d[setLabel],
                data: [],
                backgroundColor: "#"+seq[i % seq.length], 
                fill: stacked,
            };
            if(!stacked){
                ds["borderWidth"]=5;
                ds["borderColor"]="#"+seq[i % seq.length];
            }
            datasets.push(ds);
            
        }
        // get the value
        id=getIndexOf(d[setXAxis], ds.data,'x');
        cAmount= Math.abs(d[setAmount])
        if( id == -1){
            ds.data.push({x:d[setXAxis], y:cAmount});
        }else{
            v=ds.data[id];
            v.y+=cAmount;
            ds.data[id]=v;
        }
     }

    //  if(makeStackable)datasets = makeItStackable(datasets, compareDatasetDate, true);
    //  if(makeCumulative)datasets = makeItCumulative(datasets);
    datasets = makeItStackable(datasets, compareDatasetDate, makeCumulative);
     return datasets;
    
}
function makeItCumulative(datasets){
    for(var id in datasets){
        item=datasets[id];
        curr=0;
        for(i = 0 ; i< item.data.length; i++){
            // labems
            curr+=item.data[i]['y']
            item.data[i]['y']=curr;            
        }
    }
    return datasets
}
function makeItStackable(datasets, sortFunction, stackValues=False){
    // get all x axis
    var labels=[]
    for(var id in datasets){
        item=datasets[id]
        // item.data=item.data.sort(sortFunction)
        curr=0
        
        for(i = 0 ; i< item.data.length; i++){
            // labems
            labI=item.data[i]['x']
            if(!(labI in labels)){
                labels.push(labI)
            }
            
            // concat values 
            if(stackValues){
                curr= (item.data[i]['y'])+curr;
                item.data[i]['y']=curr;
            }
            
        }
        datasets[id]=item
    }
    labels=labels.sort()
    for(var id in datasets){
        items=datasets[id]['data']
        addItem=[];
        curr=0;

        for(i in labels){
            lab = labels[i]
            ind=getIndexOf(lab,items,'x')
            if(ind==-1){
                addItem.push({'x':lab, 'y':curr});
            }else{
                curr=items[ind]['y'];
            }
        }
        items=items.concat(addItem)
        items=items.sort(sortFunction)
        datasets[id]['data']=items
    }
    
    return datasets

}

function getIndexOf(key, arr, arrKey){
    for (i = 0; i < arr.length ; i++) { 
        if(arr[i][arrKey] == key)return i;
    }
    return -1;
}
function compareDatasetDate(a, b){
    if ( a.x < b.x ){
        return -1;
    }
    if ( a.x > b.x ){
        return 1;
    }
    return 0;
}

