"""Display and navigation functionality on OSM tiles.

@see: http://wiki.openstreetmap.org/wiki/Tile
@see: http://wiki.openstreetmap.org/wiki/Slippy_map_tilenames
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
# Created: Nov 30, 2009
# Modified: $Date$
#       by: $Author: $
#
#endif
__version__ = '$Id: $'

import os
import gtk
import math
import urllib
import logging

import geospace

from utils import init_logging
from geospace import GeospaceCanvas
from geospace import GeospaceToolbar

LOGGER = logging.getLogger('osmtileview-logger')
init_logging(LOGGER)

class OSMTileView(GeospaceCanvas):

    _BASE_URL = 'http://tile.openstreetmap.org/mapnik/'
    _TILE_PIXELS = 256
    _tile_cols = []
    center = (-10.0, 20.0)
    zoom = 5

    def __init__(self, geospace_activity):
        GeospaceCanvas.__init__(self)
        self._control = _Control(self)
        self.viewport.connect_after("expose_event", self.expose_cb)

        self.hbox = gtk.HBox()
        self.fixed.put(self.hbox, 0, 0)

    def expose_cb(self, widget, event):
        """Get map tiles for the currently set center, zoom value and size."""
        LOGGER.debug('expose viewport of osmtilesview')

        rect = widget.get_allocation()
        width, height = (float(rect.width), float(rect.height))
        n_xtiles = int(math.ceil(width / self._TILE_PIXELS))
        n_ytiles = int(math.ceil(height / self._TILE_PIXELS))
        #LOGGER.debug('# Tiles: %s,%s' % (n_xtiles, n_ytiles))

        # xtile/ytile shall be the middle tile
        x_tile_range = n_xtiles / 2.0
        y_tile_range = n_ytiles / 2.0

        count = len([self.hbox.remove(vtiles) for vtiles in self._tile_cols])
        del self._tile_cols[:]
        LOGGER.debug('%s items removed' % count)

        x_num, y_num = deg2num(self.center[0], self.center[1], self.zoom)
        for i_x in range(-(n_xtiles / 2), int(x_tile_range)):
            n_x = x_num + i_x
            vbox = gtk.VBox()
            for i_y in range(-(n_ytiles / 2), int(y_tile_range)):
                n_y = y_num + i_y
                file_ = '/tmp/%s_%s_%s.png' % (self.zoom, n_x, n_y)
                request = self._get_request(self.zoom, n_x, n_y)
                LOGGER.debug(request)
                response = urllib.urlopen(request)
                if not os.path.exists(file_):
                    tmp = open(file_, 'w')
                    tmp.write(response.read())
                    tmp.close()
                image = gtk.Image()
                image.set_from_file(file_)
                vbox.pack_start(image)
            self.hbox.pack_start(vbox)
            self._tile_cols.append(vbox)
        self.hbox.show_all()

    def _get_request(self, zoom, xtile_num, ytile_num):
        """Contructs request for map tile with the appropriate slippy map name.

        @param zoom: The zoom factor between 0 and 17.
        @param xtile_num: The number of the xtile.
        @param ytile_num: The number of the ytile.
        """
        return self._BASE_URL + '%s/%s/%s.png' % (zoom, xtile_num, ytile_num)

    def get_size(self):
        """Returns the views current size as tuple (width, height)."""
        rect = self.get_allocation()
        return (float(rect.width), float(rect.height))

    def get_map_coords(self):
        """Returns the map coordinate of the mouse pointer.

        @see: geospace.GeoSpace#get_map_coords()
        """
        #XXX return correct map coords
        return (int(self.x_pixel), int(self.y_pixel))

    def register_toolbars(self, toolbox):
        """Registers controller for this view."""
        map_toolbar = _MapToolbar(self, self._control)
        toolbox.add_toolbar(map_toolbar.title, map_toolbar)

###############################################################################

class _Control():
    def __init__(self, tile_view):
        self.tile_view = tile_view

    def update_map(self, center, zoom):
        """Refreshes map view according to the given bounding box.

        @param center: Tuple of (lon,lat) representing the center of the area
        the user wants to see.
        @param zoom: 0 <= zoom <= 17, describing level of detail (0 => world).
        """
        pass

###############################################################################

class _MapToolbar(GeospaceToolbar):
    """Provides tools handling the map."""

    STEP_FACTOR = 10 # percent of boundingbox height/width
    current_zoom = 3

    def __init__(self, tile_view, control):
        """Creates toolbar containing tools to handle map.

        @param tile_view: The viewer where osm tiles  will be displayed.
        @param control: The business logic for the view.
        """
        GeospaceToolbar.__init__(self)
        self.tile_view = tile_view
        self.control = control

        #self.enable_zoom_in(self.on_zoom_in)
        #self.enable_zoom_out(self.on_zoom_out)
        self.enable_toggle_crosslines(self.tile_view)

        nav_callbacks = (self.on_step_west, self.on_step_north, \
                         self.on_step_south, self.on_step_east)
        self.enable_navigation(nav_callbacks)
        self.show()

    def on_step_north(self, button):
        """Steps north of height of the current boundingbox."""
        LOGGER.debug('tile step north clicked.')
        bbox = self.tile_view.current_bbox
        zoom = self.tile_view.current_zoom
        bbox.move_north()
        self.control.update_map(bbox.get_center(), zoom)

    def on_step_east(self, button):
        """Steps east of height of the current boundingbox."""
        LOGGER.debug('tile step east clicked.')
        bbox = self.tile_view.current_bbox
        zoom = self.tile_view.current_zoom
        bbox.move_east()
        self.control.update_map(bbox.get_center(), zoom)

    def on_step_south(self, button):
        """Steps south of height of the current boundingbox."""
        LOGGER.debug('tile step south clicked.')
        bbox = self.tile_view.current_bbox
        zoom = self.tile_view.current_zoom
        bbox.move_south()
        self.control.update_map(bbox.get_center(), zoom)

    def on_step_west(self, button): #IGNORE:W0613
        """Steps west of height of the current boundingbox."""
        LOGGER.debug('tile step west clicked.')
        bbox = self.tile_view.current_bbox
        zoom = self.tile_view.current_zoom
        bbox.move_west()
        self.control.update_map(bbox.get_center(), zoom)

###########################  FUNTIONS  ########################################

def deg2num(lat_deg, lon_deg, zoom):
    """Calculates tile numbers from given parameters.

    @param lat_deg: The latitude angle of tile center.
    @param lon_deg: The longitude angle of tile center.
    @param zoom: The zoom level.
    @see: http://wiki.openstreetmap.org/wiki/Slippy_map_tilenames#Python
    """
    lat_rad = math.radians(lat_deg)
    n_tiles = 2.0 ** zoom
    xtile = int((lon_deg + 180.0) / 360.0 * n_tiles)
    ytile = int((1.0 - math.log(math.tan(lat_rad) + (1 / math.cos(lat_rad))) / \
                 math.pi) / 2.0 * n_tiles)
    return(xtile, ytile)

def num2deg(xtile, ytile, zoom):
    """Returns the NW-corner of the square.

    Use the function with xtile+1 and/or ytile+1 to get the other corners. With
    xtile+0.5 & ytile+0.5 it will return the center of the tile.

    @param xtile: The number of the xtile.
    @param ytile: The number of the ytile.
    @param zoom: The zoom factor.
    @see: http://wiki.openstreetmap.org/wiki/Slippy_map_tilenames#Python
    """
    n = 2.0 ** zoom
    lon_deg = xtile / n * 360.0 - 180.0
    lat_rad = math.atan(math.sinh(math.pi * (1 - 2 * ytile / n)))
    lat_deg = math.degrees(lat_rad)
    return(lat_deg, lon_deg)

def num_tiles(zoom):
    return 2 ^ zoom

