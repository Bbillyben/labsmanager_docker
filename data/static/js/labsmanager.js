


// --------------------     Basic Function    ------------------- // 

/**
 * get the cookie information (
 * @param {*} name : the nema of the value to retrieve
 * @returns 
 */
function getCookie(name) {
    let cookieValue = null;
    if (document.cookie && document.cookie !== '') {
        const cookies = document.cookie.split(';');
        for (let i = 0; i < cookies.length; i++) {
            const cookie = cookies[i].trim();
            if (cookie.substring(0, name.length + 1) === (name + '=')) {
                cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                break;
            }
        }
    }
    return cookieValue;
}

/**
 *  Test if an html element is empty
 * @param {*} el : the elemetn to test
 * @returns true if empty or false if filled
 */
function isEmpty( el ){
    return !$.trim(el.html())
}
$.fn.exists = function() {
    return this.length > 0;
};
$.fn.isEmpty = function() {
    return this.length > 0;
};



// params in windows
$.urlParam = function(name) {
    // eslint-disable-next-line no-useless-escape
    var results = new RegExp('[\?&]' + name + '=([^&#]*)').exec(window.location.href);

    if (results == null) {
        return null;
    }

    return decodeURI(results[1]) || 0;
};

// ---------------------- local data storage
/**
 * Save a key:value pair to local storage
 * @param {String} name - settting key
 * @param {String} value - setting value
 */
 function labSave(name, value) {

    var key = `labsmanager-${name}`;
    localStorage.setItem(key, value);
}


/**
 * Retrieve a key:value pair from local storage
 * @param {*} name - setting key
 * @param {*} defaultValue - default value (returned if no matching key:value pair is found)
 * @returns
 */
function labLoad(name, defaultValue) {

    var key = `labsmanager-${name}`;

    var value = localStorage.getItem(key);

    if (value == null) {
        return defaultValue;
    } else {
        return value;
    }
}

// -------------------- function to load a card with class loadingCard and data-url pointing to the card view url -----//

function loadCards(panel_id=""){
    // console.log("start loadCards / panel :"+panel_id);
    var selector = '.loadingCard';
    if(panel_id){
        selector = '#panel-'+panel_id+' '+selector;
    }
    $(selector).each(function(){
        url=$(this).data('url');
        if(url==undefined)return;
        loadInTemplate(elt=$(this),url=url);
    });
}

  // ------------------  ajax load direct --------------  //

  function loadInTemplate(elt, url, data={}, callback=null,type="GET", replace=false){

    csrftoken = getCookie('csrftoken');
    defaults={
        csrfmiddlewaretoken: csrftoken
    }
    var datas = $.extend(defaults, data);
    $.ajax({
        type:type,
        url: url,
        data:datas,
        success: function( data )
        {
            if(replace){
                elt.replaceWith(data);
            }else{
                elt.html(data);
            }
            
            if(callback)callback();
        },
        error:function( err )
        {
             $("body").html(err.responseText)
            //console.log(JSON.stringify(err));
        }
    })

  }

  

  