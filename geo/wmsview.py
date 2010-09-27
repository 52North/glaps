"""
View for linking an OGC Web Mapping Service (WMS) to the Geo framework.
"""
#ifndef DOXYGEN_SHOULD_SKIP_THIS
#
# Copyright (C) 2009
# by 52 North Initiative for Geospatial Open Source Software GmbH
#
# Contact: Andreas Wytzisk
# 52 North Initiative for Geospatial Open Source Software GmbH
# Martin-Luther-King-Weg 24
# 48155 Muenster, Germany
# info@52north.org
#
# This program is free software; you can redistribute and/or modify it
# under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation.
#
# This program is distributed WITHOUT ANY WARRANTY; even without the
# implied WARRANTY OF MERCHANTABILITY or FITNESS FOR A PARTICULAR
# PURPOSE. See the GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program (see gnu-gpl v2.txt). If not, write to the Free
# Software Foundation, Inc., 59 Temple Place - Suite 330, Boston,
# MA 02111-1307, USA or visit the Free Software Foundation web page,
# http://www.fsf.org.
#
# @author: Henning Bredel
# Created: Nov 25, 2009
# Modified: $Date$
#       by: $Author: $
#
#endif
__version__ = '$Id: $'

import os
import gtk
import logging

import geo
import constants

from time import time
from owslib.wms import WebMapService

from utils import _
from geo import BoundingBox
from geo import GeoCanvas
from geo import GeoToolbar

from sugar.graphics.toolbutton import ToolButton


###############################################################################

class WMSView(GeoCanvas):
    """View showing map data from a OGC Web Mapping Service."""

    # TODO getLegendGraphic
    # TODO getStyles

    image = None

    def __init__(self, activity):
        """Creates view and connects to the default WMS."""
        GeoCanvas.__init__(self, activity)
        self._logger = logging.getLogger('wms-logger')

        self._control = _Controller(self)

    def get_map_coords(self):
        """Returns the map coordinate of the mouse pointer.

        @see: geo.Geo#get_map_coords()
        """
        #XXX return correct map coords
        return (int(self.x_pixel), int(self.y_pixel))

    def display_map(self, file_):
        """Displays the map tile from a file.

        @param file_: Path to the file to be displayed.
        """
        pixbuf = gtk.gdk.pixbuf_new_from_file(file_)
        self.drawable.draw_map(pixbuf, 0, 0)
        self.canvas.queue_draw()

    def get_world_cursor(self):
        """
        Returns the cursors coordinates for the specified geo instance.

        @return: A tuple (lon,lat) of geographic WGS84 coordinates.
        """
        pass

    def get_screen_coords(self, pos):
        """
        Returns the cursors screen coordinates for the given coordinates.

        @param pos: The position data in lon/lat.
        @return: A tuple (x,y) representing the given lon/lat coordiantes.
        """
        pass

    def register_toolbars(self, toolbox):
        """Registers controllers for this view."""

        wms_toolbar = _WMSToolbar(self, self._control)
        map_toolbar = _MapToolbar(self, self._control)

        toolbox.add_toolbar(wms_toolbar.title, wms_toolbar)
        toolbox.add_toolbar(map_toolbar.title, map_toolbar)

###############################################################################

class _Controller():
    """Contains most business logic and WMS client functionality."""

    _FORMAT = 'image/png'
    _SRS = 'EPSG:4326'
    _VERSION = '1.1.1'

    def __init__(self, wms_view):

        self._logger = logging.getLogger('wms-control')
        self.wms_view = wms_view
        self.wms = None
        self.display_layers = None

    def connect_to_wms(self, url, display_layers):
        """Connects to WMS with given URL.

        @param url: The WMS URL where to connect to.
        @param display_layers: The layers the WMS shall render as map.
        """
        self.wms = WebMapService(url, self._VERSION)
        self.display_layers = display_layers

        self._logger.debug('WMS: %s' % url)
        self._logger.debug('WMS contents: %s' % self.wms.contents)
        self._logger.debug('display_layers: %s ' % display_layers )

    def update_map(self, bbox):
        """Re-requests the current WMS with a new boundingbox."""
        size_width = float(self.wms_view.get_allocation().width)
        size_height = float(self.wms_view.get_allocation().height)
        size = (size_width, size_height)
        self._request_map(bbox, size)

    def perform_getmap(self, bbox=None):
        """Sends a GetMap request and let the wms view display the response.

        @note: if bbox is or entries are None, bbox will cover biggest extent.
        @param bbox: Which spatial extent the map shall have, in form of the
        following list: [minX, minY, maxX, maxY], where longitude is along the
        x-axis and latitude along the y-axis.
        """
        if not self.wms:
            self._logger.info('No connection to a WMS established, yet.')
            return

        size_width = float(self.wms_view.get_allocation().width)
        size_height = float(self.wms_view.get_allocation().height)
        size_ratio = size_height/size_width
        size = (size_width, size_height)

        if bbox is None or bbox.lon_min is None:
            # get maximum extent
            layers = self.wms.contents
            bbox = self.wms_view.current_bbox
            for display_layer in self.display_layers:
                x_min, y_min, x_max, y_max = layers[display_layer].boundingBoxWGS84
                # is NOT a ows:WGS84BoundingBox which has lat/lon ordering!
                # WMS specification says for geographic CRS like EPSG:4326
                # "Longitude along the X-axis and Latitude along the Y-axis"
                # @see: (OGC 01-068r3, p.15)
                bbox.merge(BoundingBox(x_min, y_min, x_max, y_max))

        # Stretch boundingbox to fit current size of view
        bbox_width = bbox.get_hrange()
        bbox_height = bbox.get_vrange()
        if bbox_height < bbox_width:
            bias = bbox_height * size_ratio
            bbox.lat_min = bbox.get_south() + bbox_height / 2.0 - bias
            bbox.lat_max = bbox.get_south() + bbox_height / 2.0 + bias
        elif bbox_width < bbox_height:
            bias = bbox_width * size_ratio
            bbox.lon_min = bbox.get_west() + bbox_width / 2.0 - bias
            bbox.lon_max = bbox.get_west() + bbox_width / 2.0 + bias

        self._logger.debug('size ratio %s' % size_ratio)
        self._logger.debug('bbox ratio %s' % bbox.get_ratio())

        self._request_map(bbox, size)

    def _request_map(self, bbox, size):
        """Requests the map from WMS."""
        bbox_tuple = (bbox.get_west(), bbox.get_south(), bbox.get_east(), bbox.get_north())
        self._logger.debug("bbox: W=%s S=%s E=%s N=%s" % bbox_tuple)
        img = self.wms.getmap(layers=self.display_layers, bbox=bbox_tuple, \
                              format=self._FORMAT, size=size, \
                              srs=self._SRS, transparent=True)

        # Write map to a tmp file
        file_ = '/tmp/wms_' + str(long(time())) + '.png'
        tmp = open(file_, 'w')
        tmp.write(img.read())
        tmp.close()

        self.wms_view.display_map(file_)

###############################################################################

class _MapToolbar(GeoToolbar):
    """Provides tools handling the map."""

    def __init__(self, wms_view, control):
        """Creates toolbar containing tools to handle map.

        @param wms_view: The wms viewer where map will be displayed.
        @param control: The business logic for the view.
        """
        GeoToolbar.__init__(self, wms_view)
        self._logger = logging.getLogger('navigation-toolbar')

        self.wms_view = wms_view
        self.control = control

        # enable zooming
        zoom_callbacks = {
                  'zoom_in' : self._on_zoom_in,
                  'zoom_out': self._on_zoom_out
                  }
        self.enable_zoom(zoom_callbacks)

        # enable navigation
        nav_callbacks = {
                 'north': self._on_step_north,
                 'east' : self._on_step_east,
                 'west' : self._on_step_west,
                 'south': self._on_step_south
                 }
        self.enable_navigation(nav_callbacks)

        self.show()

    def _on_step_north(self, button):
        """Steps north of height of the current boundingbox."""
        self._logger.debug('wms step north clicked.')
        current_bbox = self.wms_view.current_bbox
        # TODO implement navigation (0.75% of current bbox)
#        self.control.update_map(current_bbox)

    def _on_step_east(self, button):
        """Steps east of height of the current boundingbox."""
        self._logger.debug('wms step east clicked.')
        current_bbox = self.wms_view.current_bbox
        # TODO implement navigation (0.75% of current bbox)
#        self.control.update_map(current_bbox)

    def _on_step_south(self, button):
        """Steps south of height of the current boundingbox."""
        self._logger.debug('wms step south clicked.')
        current_bbox = self.wms_view.current_bbox
        # TODO implement navigation (0.75% of current bbox)
#        self.control.update_map(current_bbox)

    def _on_step_west(self, button): #IGNORE:W0613
        """Steps west of height of the current boundingbox."""
        self._logger.debug('wms step west clicked.')
        current_bbox = self.wms_view.current_bbox
        # TODO implement navigation (0.75% of current bbox)
#        self.control.update_map(current_bbox)

    def _on_zoom_in(self, button):
        self._logger.debug('wms zoom in clicked.')
        current_bbox = self.wms_view.current_bbox
        # TODO implement zooming (0.75% of current bbox)

    def _on_zoom_out(self, button):
        self._logger.debug('wms zoom out clicked.')
        # TODO implement zooming (1.25% of current bbox)

    def _on_zoom_bestfit(self, button):
        self._logger.debug('wms zoom bestfit clicked.')
        bbox = self.wms_view.current_bbox
        bbox.reset()
        self.control.perform_getmap(bbox)

###############################################################################

class _WMSToolbar(gtk.Toolbar):
    """Provides tools to connect to one of the default WMS instances.

    TODO Provide also a combobox for layers?
    """
    _DEFAULT_WMS = os.path.join(constants.BUNDLE_PATH, 'config/default_wms')

    title = _('WMS Tools')

    def __init__(self, wms_view, control):
        """Creates toolbar containing tools to handle WMS.

        @param wms_view: The wms viewer where map will be displayed.
        @param control: The business logic for the view.
        """
        gtk.Toolbar.__init__(self)
        self._logger = logging.getLogger('wms-toolbar')

        self.wms_view = wms_view
        self.control = control

        self.default_wmss = {} # {url: [layers to display]}
        self._read_default_wmss()

        # prepare WMS combobox
        label = gtk.Label('WMS: ')
        label_item = gtk.ToolItem()
        label_item.add(label)
        self.insert(label_item, -1)
        combo_box = gtk.combo_box_new_text()
        combo_box.connect("changed", self.wms_selection_change_cb)
        combo_box.append_text('')
        for wms in self.default_wmss:
            combo_box.append_text(wms)
        combo_box.set_active(0)
        cb_item = gtk.ToolItem()
        cb_item.add(combo_box)
        self.insert(cb_item, -1)

        refresh_map_btn = ToolButton('reload')
        refresh_map_btn.set_tooltip(_('Refresh Map.'))
        bbox = self.wms_view.current_bbox
        refresh_map_btn.connect('clicked', self.update_map_cb, bbox)
        refresh_map_btn.show()
        self.insert(refresh_map_btn, -1)

        self.show_all()

    def update_map_cb(self, button, bbox):
        """Reloads the map with current bbox."""
        if bbox.lon_min is None:
            return
        self._logger.debug('Reload map with bbox: %s' % bbox)
        self.control.update_map(bbox)

    def wms_selection_change_cb(self, combo_box):
        """Connects to selected WMS and performs getMap request.

        @param combo_box: The combobox selection event was triggered.
        """
        url = combo_box.get_active_text()
        if not url or len(url) == 0:
            return
        self.control.connect_to_wms(url, self.default_wmss[url])
        self.wms_view.current_bbox.reset()
        self.control.perform_getmap()

    def _read_default_wmss(self):
        """Returns list containing the default WMS instances read from
        `config/default_wms').
        """
        file_ = None
        try:
            file_ = open(self._DEFAULT_WMS, 'r')
            read_data = file_.readlines()
            for line in read_data:
                url, layers = _extract_wms_info(line)
                if url is not None:
                    self.default_wmss[url] = layers
        except IOError:
            self._logger.debug('Could not read file %s' % self._DEFAULT_WMS)
            file_.close()

        self._logger.debug('Default WMS(s) read: %s' % self.default_wmss)

###########################  FUNCTIONS  #######################################

def _extract_wms_info(line):
    """Returns URL and list of layers.

    @param line: the URL and a list of layers. If line is a comment or
    empty, None is returned twice.
    @return: A tuple of URL and its list of layers to be displayed.
    """
    line = line.strip()
    if line.startswith('#') or len(line) == 0:
        return None, None
    else:
        url_and_layers = line.split(';')
        return url_and_layers[0].strip(), \
               [layer.strip() for layer in url_and_layers[1].split(',')]

