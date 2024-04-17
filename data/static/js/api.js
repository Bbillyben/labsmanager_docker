/* Credit : Inventree https://github.com/inventree/InvenTree
*/

// $.urlParam = function(name) {
//     // eslint-disable-next-line no-useless-escape
//     var results = new RegExp('[\?&]' + name + '=([^&#]*)').exec(window.location.href);

//     if (results == null) {
//         return null;
//     }

//     return decodeURI(results[1]) || 0;
// };


function labsmanagerGet(url, filters={}, options={}) {

    // Middleware token required for data update
    var token = getCookie('csrftoken');

    return $.ajax({
        beforeSend: function(xhr) {
            xhr.setRequestHeader('X-CSRFToken', csrftoken);
        },
        url: url,
        type: 'GET',
        data: filters,
        dataType: 'json',
        contentType: 'application/json',
        async: (options.async == false) ? false : true,
        success: function(response) {
            if (options.success) {
                options.success(response);
            }
        },
        error: function(xhr, ajaxOptions, thrownError) {
            console.error('Error on GET at ' + url);

            if (thrownError) {
                console.error('Error: ' + thrownError);
            }

            if (options.error) {
                options.error({
                    error: thrownError
                });
            } else {
                showApiError(xhr, url);
            }
        }
    });
}

function labsmanagerFormDataUpload(url, data, options={}) {
    /* Upload via AJAX using the FormData approach.
     *
     * Note that the following AJAX parameters are required for FormData upload
     *
     * processData: false
     * contentType: false
     */

    // CSRF cookie token
    var csrftoken = getCookie('csrftoken');

    return $.ajax({
        beforeSend: function(xhr) {
            xhr.setRequestHeader('X-CSRFToken', csrftoken);
        },
        url: url,
        method: options.method || 'POST',
        data: data,
        processData: false,
        contentType: false,
        success: function(data, status, xhr) {
            if (options.success) {
                options.success(data, status, xhr);
            }
        },
        error: function(xhr, status, error) {
            console.error('Form data upload failure: ' + status);

            if (options.error) {
                options.error(xhr, status, error);
            } else {
                showApiError(xhr, url);
            }
        }
    });
}

function labsmanagerPut(url, data={}, options={}) {

    var method = options.method || 'PUT';

    // Middleware token required for data update
    var csrftoken = getCookie('csrftoken');

    return $.ajax({
        beforeSend: function(xhr) {
            xhr.setRequestHeader('X-CSRFToken', csrftoken);
        },
        url: url,
        type: method,
        data: JSON.stringify(data),
        dataType: 'json',
        contentType: 'application/json',
        success: function(response, status) {
            if (options.success) {
                options.success(response, status);
            }
            if (options.reloadOnSuccess) {
                location.reload();
            }
        },
        error: function(xhr, ajaxOptions, thrownError) {
            if (options.error) {
                options.error(xhr, ajaxOptions, thrownError);
            } else {
                console.error(`Error on ${method} to '${url}' - STATUS ${xhr.status}`);
                console.error(thrownError);

                showApiError(xhr, url);
            }
        },
        complete: function(xhr, status) {
            if (options.complete) {
                options.complete(xhr, status);
            }
        }
    });
}


/*
 * Display a notification with error information
 */
function showApiError(xhr, url) {

    var title = null;
    var message = null;

    if (xhr.statusText == 'abort') {
        // Don't show errors for requests which were intentionally aborted
        return;
    }

    switch (xhr.status || 0) {
    // No response
    case 0:
        title = '{% trans "No Response" %}';
        message = '{% trans "No response from the LabsManager server" %}';
        break;
    // Bad request
    case 400:
        // Note: Normally error code 400 is handled separately,
        //       and should now be shown here!
        title = '{% trans "Error 400: Bad request" %}';
        message = '{% trans "API request returned error code 400" %}';
        break;
    // Not authenticated
    case 401:
        title = '{% trans "Error 401: Not Authenticated" %}';
        message = '{% trans "Authentication credentials not supplied" %}';
        break;
    // Permission denied
    case 403:
        title = '{% trans "Error 403: Permission Denied" %}';
        message = '{% trans "You do not have the required permissions to access this function" %}';
        break;
    // Resource not found
    case 404:
        title = '{% trans "Error 404: Resource Not Found" %}';
        message = '{% trans "The requested resource could not be located on the server" %}';
        break;
    // Method not allowed
    case 405:
        title = '{% trans "Error 405: Method Not Allowed" %}';
        message = '{% trans "HTTP method not allowed at URL" %}';
        break;
    // Timeout
    case 408:
        title = '{% trans "Error 408: Timeout" %}';
        message = '{% trans "Connection timeout while requesting data from server" %}';
        break;
    default:
        title = '{% trans "Unhandled Error Code" %}';
        message = `{% trans "Error code" %}: ${xhr.status}`;

        var response = xhr.responseJSON;

        // The server may have provided some extra information about this error
        if (response) {
            if (response.error) {
                title = response.error;
            }

            if (response.detail) {
                message = response.detail;
            }
        }

        break;
    }

    if (url) {
        message += '<hr>';
        message += `URL: ${url}`;
    }

    showMessage(title, {
        style: 'danger',
        icon: 'fas fa-server icon-red',
        details: message,
    });
}
function showMessage(message, options={}) {

    var style = options.style || 'info';

    var timeout = options.timeout || 5000;

    var target = options.target || $('#alerts');

    var details = '';

    if (options.details) {
        details = `<p><small>${options.details}</p></small>`;
    }

    // Hacky function to get the next available ID
    var id = 1;

    while ($(`#alert-${id}`).exists()) {
        id++;
    }

    var icon = '';

    if (options.icon) {
        icon = `<span class='${options.icon}'></span>`;
    }

    // Construct the alert
    var html = `
    <div id='alert-${id}' class='alert alert-${style} alert-dismissible fade show' role='alert'>
        ${icon}
        <b>${message}</b>
        ${details}
        <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
    </div>
    `;

    target.append(html);

    // Remove the alert automatically after a specified period of time
    $(`#alert-${id}`).delay(timeout).slideUp(200, function() {
        $(this).alert(close);
    });
}
