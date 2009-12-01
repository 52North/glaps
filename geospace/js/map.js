/*
 * map.js
 *
 * TODO add a small description here.
 */

var map = null;

var x = null;
var y = null;

function init() {

	map = new OpenLayers.Map('map');

	var ol_wms = new OpenLayers.Layer.WMS("OpenLayers WMS",
			"http://labs.metacarta.com/wms/vmap0", {
				layers :'basic'
			});

	map.addLayer(ol_wms);
	map.addControl(new OpenLayers.Control.LayerSwitcher());
	map.zoomToMaxExtent();
}

function setCenter(lon, lat) {
	var lonlat = new OpenLayers.LonLat(lon, lat);
	map.panTo(lonlat);
}
