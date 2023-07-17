/*
 * Sanitize a string provided by the user from an input field,
 * e.g. data form or search box
 *
 * - Remove leading / trailing whitespace
 * - Remove hidden control characters
 *  Credit : Inventree https://github.com/inventree/InvenTree
 */
function sanitizeInputString(s, options={}) {

    if (!s) {
        return s;
    }

    // Remove ASCII control characters
    s = s.replace(/[\x01-\x1F]+/g, '');

    // Remove Unicode control characters
    s = s.replace(/[\p{C}]+/gu, '');

    s = s.trim();

    return s;
}

/**
 * Format a float number to reflect a percentage.
 *
 * @returns {String}
 */

 function quotityDisplay(value){
    return parseFloat(value*100).toFixed(0)+" %";
}

/**
 * Format a float number to reflect currency in euros (not use € as it crash bottstraptable export).
 *
 * @returns {String}
 */
function moneyDisplay(value){
    formatter = new Intl.NumberFormat('fr-FR', {
        style: 'currency',
        currency: 'EUR',
        minimumFractionDigits: 0,
        maximumFractionDigits: 2,
      });
    return formatter.format(value); //.replaceAll(',', ' ')+" EUR";

}

/**
 * Determine whether the given `input` is iterable.
 *
 * @returns {Boolean}
 */
 function isIterable(input) {  
    if (input === null || input === undefined) {
      return false
    }
  
    return typeof input[Symbol.iterator] === 'function'
  }


  
/**
 * Returns true if the input looks like a valid number
 * @param {String} n
 * @returns
 */
function isNumeric(n) {
  return !isNaN(parseFloat(n)) && isFinite(n);
}

/**
 * Returns true if the input looks like a json
 * @param {String} n
 * @returns
 */
function isJson(item) {
  let value = typeof item !== "string" ? JSON.stringify(item) : item;
  try {
    value = JSON.parse(value);
  } catch (e) {
    return false;
  }

  return typeof value === "object" && value !== null;
}

/**
 * Returns true if the input looks like a email
 * @param {String} n
 * @returns
 */
function isEmail(item) {
  var validRegex = /^[a-zA-Z0-9.!#$%&'*+/=?^_`{|}~-]+@[a-zA-Z0-9-]+(?:\.[a-zA-Z0-9-]+)*$/;
  return item.match(validRegex);
}

/**
 * To replicate windows open with POST params.
 * Create a Form and submit it 
 * @returns nothing
 */
function openWindowWithPost(url, data, csrftoken) {
  var form = document.createElement("form");
  form.target = "_blank";
  form.method = "POST";
  form.action = url;
  form.style.display = "none";
  form.header

  for (var key in data) {
      var input = document.createElement("input");
      input.type = "hidden";
      input.name = key;
      input.value = data[key];
      form.appendChild(input);
  }
  const hiddenField = document.createElement('input');
  hiddenField.type = 'hidden';
  hiddenField.name = 'csrfmiddlewaretoken';
  hiddenField.value = csrftoken;
  form.appendChild(hiddenField);

  document.body.appendChild(form);



  form.submit();
  document.body.removeChild(form);
}