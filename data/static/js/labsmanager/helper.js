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