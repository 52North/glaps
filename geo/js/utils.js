/*
 * utils.js
 *
 * Aggregates utility methods probably not only used by one js file.
 */

SERVER = "http://127.0.0.1:24242";

/**
 * Sends a XMLHttpRequest tto the specified Url and returns the
 *
 * @param {String}
 *            verb REST type (GET, POST, UPDATE, DELETE)
 * @param {String}
 *            postData Text that should be sendet with the post statement
 * @param {Function}
 *            respFunc Function that sould be the onreadystatechange methode
 */
function sendPostRequest(verb, postData, respFunc) {
	var req = getXMLRequest();

	if (req == null) {
		return;
	}

	req.onreadystatechange = function() {
		if (req.readyState == 4) {
			if (req.status == 200) {
				respFunc(req)
			} else {
				// TODO handle
			}
		}
	};
	req.open(verb, SERVER, true);
	req.send(postData);

	return req;
}

function getXMLRequest() {
	// Generate an xmlhttprequest
	var xmlhttp = false;
	if (!xmlhttp && typeof XMLHttpRequest != 'undefined') {
		try {
			xmlhttp = new XMLHttpRequest();
		} catch (e) {
			xmlhttp = false;
		}
	}
	if (!xmlhttp && window.createRequest) {
		try {
			xmlhttp = window.createRequest();
		} catch (e) {
			xmlhttp = false;
		}
	}
	return xmlhttp;
}

function callback() {
	alert('Response called back')
}
