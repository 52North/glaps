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
__version__ = '$Id: osmtileview.py 179 2010-09-27 08:47:24Z  $'

import os
import gtk
import math
import urllib
import logging
import threading

from sugar import profile

import utils
import geo
import position
import constants

from geo import BoundingBox
from geo import GeoCanvas
from geo import GeoToolbar
from shapely.geometry import Point

###############################################################################

class TileReceiver(threading.Thread):

    # TODO:  make this editable from the user interface? or via an application
    # that users with XOs can join to get the correct url
    _BASE_URL = 'http://tile.openstreetmap.org/mapnik/'

    def __init__(self, i, i_x, j, i_y, view):
        threading.Thread.__init__(self, target=self.render_tile, args=(i, i_x, j, i_y, view))
        self._logger = logging.getLogger('tilereceiver-logger')
        self._logger.setLevel(constants.LOG_LEVEL)
        self.zoom = view.zoom

    def render_tile(self, i, i_x, j, i_y, view):

        max = 2**(self.zoom) # highest tile-num available
        if i_x >= 0 and i_y >= 0 and i_x < max and i_y < max:
            tile_relpath = '%s/%s/' % (self.zoom, i_x)
            tile_path = os.path.join(constants.TMP_PATH, tile_relpath)
            tile_name = '%s.png' % i_y
            tile = os.path.join(tile_relpath, tile_name)
            file_ = os.path.join(constants.TMP_PATH , tile)
            #self._logger.debug(file_)

            if not os.path.exists(file_):
                if not os.path.exists(tile_path):
                    os.makedirs(tile_path, 0755)
                tile_url = self._BASE_URL + tile_relpath + tile_name
                self.get_tile(file_, tile_url)
        else:
            # out of bounds
            file_ = os.path.join(constants.TMP_PATH, '404.png')

        # draw map stuff on drawable
        pixbuf = None
        try:
            pixbuf = gtk.gdk.pixbuf_new_from_file(file_)
        except Exception, e:
            self._logger.error("Reload file '%s' (contained no data).", file_)
            file_ = os.path.join(constants.TMP_PATH, '404.png')
            pixbuf = gtk.gdk.pixbuf_new_from_file(file_)
        x_loc = i * view._TILE_PIXELS + view.x_shift
        y_loc = j * view._TILE_PIXELS + view.y_shift
        #self._logger.debug('place pixbuf to x: %s y: %s', x_loc, y_loc)
        view.drawable.draw_map(pixbuf, x_loc, y_loc)
        view.canvas.queue_draw_area(x_loc, y_loc, view._TILE_PIXELS, view._TILE_PIXELS)

    def get_tile(self, file_, tile):
        tmp = None
        try:
            #self._logger.debug("url: %s", self._BASE_URL + tile_relpath + tile_name)
            response = urllib.urlopen(tile)
            tmp = open(file_, 'w')
            tmp.write(response.read())
        except Exception, e:
            self._logger.debug("Could not load tile '%s' from URL (at zoom level %s)", tile, self.zoom)
            file_ = os.path.join(constants.TMP_PATH, '404.png')
        finally:
            if tmp:
                tmp.close()

###############################################################################

class OSMTileView(GeoCanvas):

    _TILE_PIXELS = 256
    _NX_TILES = 5
    _NY_TILES = 5
    ZOOM_MIN = 3
    ZOOM_MAX = 18

    x_shift = 0
    y_shift = 0
    center = Point(-10.0, 20.0) # !! lon,lat !!
    zoom = 4 # levels: 2--18

    x_pan_start = None
    y_pan_start = None
    pan_started = False
    panning = False

    def __init__(self, activity):
        GeoCanvas.__init__(self, activity)
        self._logger = logging.getLogger('osmtileview-logger')
        self._logger.setLevel(constants.LOG_LEVEL)
        self.connect("button_press_event", self.button_press_cb)
        self.connect("button_release_event", self.button_release_cb)
        self.connect("motion_notify_event", self.pan_motion_cb)

        self._control = _Control(self)
        if not activity.has_gps_connection():
            self._logger.debug('Less zoom factor, since no GPS connection available.')
            self.zoom = 4
        else:
            self._logger.debug('Set center to gps_position: %s', activity.gps_position)
            if activity.gps_position:
                # GPS session needs 1-2 sec to initialize
                self.center = activity.gps_position

        self.vbox.connect("expose_event", self.expose_cb)
        self.size_cb = self.connect("size_allocate", self.size_allocation_cb)

        self.show_all()

    def init_center(self, activity, position):
        self._logger.debug("_init_center()")
        player = activity.get_player()
        position = player.position
        if player.oldpos:
            got_first_position = player.oldpos.x == 0 and player.oldpos.y == 0
        if position.x != 0 and position.y != 0 and got_first_position:
            self._logger.debug("center on very first position.")
            # center on very first position
            self.map.center = position
            self.map.zoom = self.map.ZOOM_MAX
            self.map.draw_map()

            activity.disconnect(self.center_on_first_position_handler)

    def button_press_cb(self, widget, event):
        #self._logger.debug("button %s was pressed", event.button)
        if event.button == 1:
            self.pan_started = True
            self.x_pan_start = event.x
            self.y_pan_start = event.y

    def button_release_cb(self, widget, event):
        self._logger.debug("button_release_cb")
        self.pan_started = False
        if self.panning:
            self.panning = False # reset pan modus
            #self._logger.debug("x: %s y: %s", self.x_pixel, self.y_pixel)
            x_px_delta = event.x - self.x_pan_start
            y_px_delta = event.y - self.y_pan_start
            xy_center = self.get_screen_coords(self.center)
            self.center = self.get_lonlat_from(xy_center[0] - x_px_delta,
                                               xy_center[1] - y_px_delta)
            #self._logger.debug("new center: %s", self.center)
            self.change_cursor(geo.CROSS_CURSOR)
            self.draw_map()

    def pan_motion_cb(self, widget, event):
        if self.pan_started:
#            self._logger.debug("panning")
            self.panning = True
            self.change_cursor(geo.PAN_CURSOR)
        # TODO move map while dragging

    def size_allocation_cb(self, widget, allocation):
        """
        Callback to configure widget appropriately before exposing.
        """
        self._logger.debug('size_allocation_cb()')
        x, y, width, height = self.get_allocation()
#        self._logger.debug("alloc: %s, %s, %s, %s", x, y, width, height)
        self.x_shift = (width - self._NX_TILES * self._TILE_PIXELS) / 2
        self.y_shift = (height - self._NY_TILES * self._TILE_PIXELS) / 2
        self.queue_draw()
        self._logger.debug('x_shift: %d, y_shift: %d', self.x_shift, self.y_shift)
        self.disconnect(self.size_cb) # use only once

    def expose_cb(self, widget, event):
        """
        Callback to get map tiles for the current center, zoom value and size.

        @note: does repainting map only when flagged L{gtk.VISIBLE}.
        """
        x, y, w, h = event.area
        self.draw_map()

    def draw_map(self):
        """
        Draws OSM tiles on the geo's drawable.
        """
        # clear old tiles
        half_range_x = self._NX_TILES / 2.0
        half_range_y = self._NY_TILES / 2.0

        # xnum/ynum are the middle tile
        x_num, y_num = deg2num(self.center, self.zoom)
        first_x = x_num - int(half_range_x)
        first_y = y_num - int(half_range_y)
        last_x = x_num + int(half_range_x)
        last_y = y_num + int(half_range_y)

        # spatial extent: upper-left & bottom-right
        s_1st, w_1st, n_1st, e_1st = get_edges(first_x, first_y, self.zoom)
        s_last, w_last, n_last, e_last = get_edges(last_x, last_y, self.zoom)
        self.current_bbox = BoundingBox(w_1st, s_1st, e_1st, n_1st)
        self.current_bbox.merge(BoundingBox(w_last, s_last, e_last, n_last))

        # get and cache the tile
        for i, i_x in enumerate(range(first_x, last_x+1)):
            vbox = gtk.VBox()
            for j, i_y in enumerate(range(first_y, last_y+1)):
                receiver = TileReceiver(i, i_x, j, i_y, self)
                receiver.start()
                receiver.join(1)

        if self._CROSSLINES:
            self.motion_crosslines(self)

    def get_world_cursor(self):
        """
        Returns the lon/lat coordinates of the mouse pointer.

        @see: geo.GeoCanvas#get_world_cursor()
        """
        return self.get_lonlat_from(self.x_pixel, self.y_pixel)

    def get_lonlat_from(self, x_px, y_px):
        """
        Calculates lon/lat for given pixel coordinates.

        @param x_px: The x pixel.
        @param y_px: The y pixel.
        @return: Point(lon,lat) for given pixel coordinates.
        """
        bbox = self.current_bbox
        x, y, w, h = self.get_allocation()
#        self._logger.debug('alloc: %s %s %s %s', x, y, w, h)

        bbox_width_px = self._NX_TILES * self._TILE_PIXELS
        bbox_height_px = self._NY_TILES * self._TILE_PIXELS

        x_norm = float(x_px - self.x_shift) / float(bbox_width_px)
        y_norm = float(bbox_height_px - y_px + self.y_shift) / float(bbox_height_px)

        # get cursors mercator coordinates
        ll_x, ll_y = lonlat2xy(bbox.get_west(), bbox.get_south(), self.zoom)
        ur_x, ur_y = lonlat2xy(bbox.get_east(), bbox.get_north(), self.zoom)
        x_merc = ll_x + (ur_x - ll_x) * x_norm
        y_merc = ll_y + (ur_y - ll_y) * y_norm

        # reproject cursor to lon/lat
        return xy2lonlat(x_merc, y_merc, self.zoom)

    def get_screen_coords(self, pos):
        """
        Returns the (x,y) values for the given lon/lat coordinates relative
        to the current screen or None if position lays beyond the current
        spatial extent (BoundingBox).

        @param pos: The position relative values shall be calculated for.
        @return: A tuple (x,y) containing the screen coordinates for lon/lat.
        @see geo.GeoCanvas#get_xy_coords()
        """
        #self._logger.debug('get_screen_coordinates()')
        bbox = self.current_bbox
        if not self.current_bbox.contains(pos):
            #self._logger.debug('out of range .. return None')
            return None

        width = self._NX_TILES * self._TILE_PIXELS
        height = self._NY_TILES * self._TILE_PIXELS
        ll_x, ll_y = lonlat2xy(bbox.get_west(), bbox.get_south(), self.zoom)
        ur_x, ur_y = lonlat2xy(bbox.get_east(), bbox.get_north(), self.zoom)
        x_merc, y_merc = lonlat2xy(pos.x, pos.y, self.zoom)
        x_norm = float(x_merc - ll_x) / float(ur_x - ll_x)
        y_norm = float(y_merc - ll_y) / float(ur_y - ll_y)
        x_screen = int(width * x_norm) + self.x_shift
        y_screen = int(height * y_norm) - self.y_shift

        #self._logger.debug(bbox)
        #self._logger.debug('x: %1.6f y: %1.6f w: %1.6f h: %1.6f' %
        #                  (x, y, width, height))
        #self._logger.debug('lon: %1.6f lat: %1.6f' % (pos.x, pos.y))
        #self._logger.debug('x_merc: %1.6f y_merc: %1.6f' % (x_merc, y_merc))
        #self._logger.debug('xnorm: %1.6f ynorm: %1.6f' % (x_norm, y_norm))
        #self._logger.debug('llx: %1.6f lly: %1.6f' % (ll_x, ll_y))
        #self._logger.debug('urx: %1.6f ury: %1.6f' % (ur_x, ur_y))
        #self._logger.debug('x_norm: %1.6f y_norm: %1.6f' % (x_norm, y_norm))

        if (0 <= x_screen < width) and (0 <= y_screen <= height):
            x_screen, y_screen = x_screen, height - y_screen
            #self._logger.debug('x_screen: %d y_screen: %d' % (x_screen, y_screen))
            return x_screen, y_screen

    def register_toolbars(self, toolbox):
        """
        Registers controller for this view.
        """
        map_toolbar = _MapToolbar(self, self._control)
        toolbox.add_toolbar(map_toolbar.title, map_toolbar)

###############################################################################

class _Control():
    """
    Controller class for OSMTileView.
    """
    def __init__(self, tile_view):
        self.tile_view = tile_view

    def update_map(self, center=None, zoom=None):
        """
        Refreshes map view according to the given bounding box.

        @param center: Point of lon/lat representing the center of the area
        the user wants to see.
        @param zoom: 1 < zoom <= 18, describing level of detail.
        """
        if center:
            self.tile_view.center = center
        if zoom:
            self.tile_view.zoom = zoom
        self.tile_view.draw_map()

###############################################################################

class _MapToolbar(GeoToolbar):
    """
    Provides tools handling the map.
    """

    STEP_FACTOR = 25.0 # percent of boundingbox height/width

    def __init__(self, tile_view, control):
        """
        Creates toolbar containing tools to handle map.

        @param tile_view: The viewer where osm tiles will be displayed.
        @param control: The business logic for the view.
        """
        GeoToolbar.__init__(self, tile_view)
        self.tile_view = tile_view
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

        # enable position features
        self.center_signal_id = None
        if tile_view.activity.has_gps_connection():
            self.enable_center_current_position(self._on_center_on_current_position)

            #self.enable_toggle_crosslines(self.tile_view)

            separator = gtk.SeparatorToolItem()
            separator.set_draw(False)
            #separator.set_expand(True)
            separator.set_size_request(100, 30)
            self.insert(separator, -1)
            separator.show()

            self.enable_show_own_position(self.tile_view)
            self.enable_show_all_positions(self.tile_view)
            self.radio_show_all_pos_btn.set_active(True)
        else:
            #self.enable_toggle_crosslines(self.tile_view)

            separator = gtk.SeparatorToolItem()
            separator.set_draw(False)
            separator.set_size_request(100, 30)
            self.insert(separator, -1)
            separator.show()

            self.enable_show_all_positions(self.tile_view)

        self.show()

    def _on_center_on_current_position(self, button): #IGNORE:W0613
        """
        Prepares and delegates a recenter of the displayed map on the
        current position with maximum zoom level.
        """
        activity = self.tile_view.activity
        if button.get_active():
            self.step_east_btn.set_sensitive(False)
            self.step_south_btn.set_sensitive(False)
            self.step_north_btn.set_sensitive(False)
            self.step_west_btn.set_sensitive(False)
            self.zoom_in_btn.set_sensitive(False)
            self.zoom_out_btn.set_sensitive(False)
            def center_map(activity, position):
                self.control.update_map(center=position, zoom=OSMTileView.ZOOM_MAX)
            self.center_signal_id = activity.connect('position_changed', center_map)
        else:
            self.step_east_btn.set_sensitive(True)
            self.step_south_btn.set_sensitive(True)
            self.step_north_btn.set_sensitive(True)
            self.step_west_btn.set_sensitive(True)
            self.zoom_in_btn.set_sensitive(True)
            self.zoom_out_btn.set_sensitive(True)
            activity.disconnect(self.center_signal_id)

    def _on_zoom_in(self, button): #IGNORE:W0613
        """
        Zooms one step in the map.
        """
        zoom = self.tile_view.zoom
        if zoom < OSMTileView.ZOOM_MAX:
            #self._logger.debug('new zoomlevel: %d' % (zoom + 1))
            self.tile_view.change_cursor(geo.WAIT_CURSOR)
            self.control.update_map(zoom=zoom + 1)
            self.tile_view.change_cursor(geo.CROSS_CURSOR)
        else:
            self._logger.info('Cannot not zoom in further.')

    def _on_zoom_out(self, button): #IGNORE:W0613
        """
        Zooms one step out the map.
        """
        zoom = self.tile_view.zoom
        if OSMTileView.ZOOM_MIN < zoom:
            #self._logger.debug('new zoomlevel: %d' % (zoom - 1))
            self.tile_view.change_cursor(geo.WAIT_CURSOR)
            self.control.update_map(zoom=zoom - 1)
            self.tile_view.change_cursor(geo.CROSS_CURSOR)
        else:
            self._logger.info('Cannot not zoom out further.')

    def _on_step_north(self, button): #IGNORE:W0613
        """
        Steps north of height of the current boundingbox.
        """
        center = self.tile_view.center
        bbox = self.tile_view.current_bbox
        step = bbox.get_vrange() / 100.0 * self.STEP_FACTOR
        self.tile_view.change_cursor(geo.WAIT_CURSOR)
        self.control.update_map(Point(center.x, center.y + step))
        self.tile_view.change_cursor(geo.CROSS_CURSOR)

    def _on_step_east(self, button): #IGNORE:W0613
        """
        Steps east of height of the current boundingbox.
        """
        center = self.tile_view.center
        bbox = self.tile_view.current_bbox
        step = bbox.get_hrange() / 100.0 * self.STEP_FACTOR
        self.tile_view.change_cursor(geo.WAIT_CURSOR)
        self.control.update_map(Point(center.x + step, center.y))
        self.tile_view.change_cursor(geo.CROSS_CURSOR)

    def _on_step_south(self, button): #IGNORE:W0613
        """
        Steps south of height of the current boundingbox.
        """
        center = self.tile_view.center
        bbox = self.tile_view.current_bbox
        step = bbox.get_vrange() / 100.0 * self.STEP_FACTOR
        self.tile_view.change_cursor(geo.WAIT_CURSOR)
        self.control.update_map(Point(center.x, center.y - step))
        self.tile_view.change_cursor(geo.CROSS_CURSOR)

    def _on_step_west(self, button): #IGNORE:W0613
        """
        Steps west of height of the current boundingbox.
        """
        center = self.tile_view.center
        bbox = self.tile_view.current_bbox
        step = bbox.get_hrange() / 100.0 * self.STEP_FACTOR
        self.tile_view.change_cursor(geo.WAIT_CURSOR)
        self.control.update_map(Point(center.x - step, center.y))
        self.tile_view.change_cursor(geo.CROSS_CURSOR)

###########################  FUNCTIONS  #######################################


# All following functions more or less adopted from:
# http://wiki.openstreetmap.org/wiki/Slippy_map_tilenames#Python

from math import pi
from math import log
from math import tan
from math import cos
from math import atan
from math import sinh
from math import radians
from math import degrees

def deg2num(center, zoom):
    """Calculates tile numbers from given parameters.

    @param center: The lon/lat of tile center.
    @param zoom: The zoom level.
    @see: http://wiki.openstreetmap.org/wiki/Slippy_map_tilenames#Python
    """
    tilenum = num_tiles(zoom)
    lat_rad = radians(center.y)
    xtile = int((center.x + 180.0) / 360.0 * tilenum)
    ytile = int((1.0 - log(tan(lat_rad) + sec(lat_rad)) / pi) / 2.0 * tilenum)

    return xtile, ytile

def num2deg(xtile, ytile, zoom):
    """Returns the NW-corner of the square.

    Use the function with xtile+1 and/or ytile+1 to get the other corners. With
    xtile+0.5 & ytile+0.5 it will return the center of the tile.

    @param xtile: The number of the xtile.
    @param ytile: The number of the ytile.
    @param zoom: The zoom factor.
    @return: Point in lon/lat order
    @see: http://wiki.openstreetmap.org/wiki/Slippy_map_tilenames#Python
    """
    tilenum = num_tiles(zoom)
    lon_deg = xtile / tilenum * 360.0 - 180.0
    lat_rad = atan(sinh(pi * (1 - 2 * ytile / tilenum)))
    lat_deg = degrees(lat_rad)

    return Point(lon_deg, lat_deg)

def lonlat2relativeXY(lon, lat):
    """Returns a tuple (x,y)."""
    x_rel = (lon + 180) / 360
    y_rel = (1 - log(tan(radians(lat)) + sec(radians(lat))) / pi) / 2
    return x_rel, y_rel

def lonlat2xy(lon, lat, zoom):
    """Returns a tuple (x,y)."""
    tilenum = num_tiles(zoom)
    x_rel, y_rel = lonlat2relativeXY(lon, lat)
    return tilenum * x_rel, tilenum * y_rel

def xy2lonlat(x_merc, y_merc, zoom):
    """Returns a Point with lon/lat values."""
    tilenum = num_tiles(zoom)
    relY = y_merc / tilenum
    lat = mercator2lat(pi * (1 - 2 * relY))
    lon = -180.0 + 360.0 * x_merc / tilenum
    return Point(lon, lat)

def mercator2lat(mercator_y):
    """Re-projects mercator coordinate to latitude value.

    @note: parameter must be in domain [-pi,+pi].
    @param mercator_y: The mercator y value to reproject.
    @see: http://wiki.openstreetmap.org/wiki/Slippy_map_tilenames#Python
    """
    return degrees(atan(sinh(mercator_y)))

def lat_edge(ytile, zoom):
    """Returns the latitude edge of given y-tile.

    @param ytile: The y-number of tile to calculate north and south edges for.
    @param zoom: The specific zoom factor used.
    @return: Tuple containing (north-edge, south-edge).
    @see: http://wiki.openstreetmap.org/wiki/Slippy_map_tilenames#Python
    """
    tilenum = num_tiles(zoom)
    unit = 1 / tilenum
    rel_y1 = ytile * unit
    rel_y2 = rel_y1 + unit
    lat1 = mercator2lat(pi * (1 - 2 * rel_y1))
    lat2 = mercator2lat(pi * (1 - 2 * rel_y2))

    return lat1, lat2

def lon_edge(xtile, zoom):
    """Returns the longitude edge of given x-tile.

    @param ytile: The x-number of tile to calculate east and west edges for.
    @param zoom: The specific zoom factor used.
    @return: Tuple containing (west-edge, east-edge).
    @see: http://wiki.openstreetmap.org/wiki/Slippy_map_tilenames#Python
    """
    tilenum = num_tiles(zoom)
    unit = 360 / tilenum
    lon1 = -180 + xtile * unit
    lon2 = lon1 + unit

    return lon1, lon2

def get_edges(xtile, ytile, zoom):
    """Returns the edges of the given tile.

    @param xtile: The x-number of tile to calculate east and west edges for.
    @param ytile: The y-number of tile to calculate north and south edges for.
    @param zoom: The specific zoom factor used.
    @return: tuple of (S,W,N,E) edges in geographic WGS84.
    @see: http://wiki.openstreetmap.org/wiki/Slippy_map_tilenames#Python
    """
    lat1, lat2 = lat_edge(ytile, zoom)
    lon1, lon2 = lon_edge(xtile, zoom)

    return (lat2, lon1, lat1, lon2) # S,W,N,E

def num_tiles(zoom):
    """Returns the number of tiles."""
    return 2.0 ** zoom

def sec(rad):
    """Returns sec = 1/cos."""
    return 1.0 / cos(rad)
