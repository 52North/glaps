"""Module defining the general geospace classes and functionality."""
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

import gtk
import gobject
import logging

from sugar.activity import activity
from sugar.graphics.toolbutton import ToolButton
from sugar.graphics.toggletoolbutton import ToggleToolButton

from utils import _
from utils import init_logging

BUNDLE_PATH = activity.get_bundle_path()
CROSS_CURSOR = gtk.gdk.Cursor(gtk.gdk.CROSSHAIR)
ARROW_CURSOR = gtk.gdk.Cursor(gtk.gdk.ARROW)
PAN_CURSOR = gtk.gdk.Cursor(gtk.gdk.FLEUR)
INIT_CROSSLINE = True
LOGGER = logging.getLogger('geospace-logger')
init_logging(LOGGER)

###############################################################################

class GeospaceCanvas(gtk.Fixed):
    """Serves as basic space which observes the current mouse position.

    The general GeospaceCanvas has no knowledge of the concrete CRS which is
    being used (within RasterView or WMSView). The canvas CRS is the standard
    screen system which has its origin on the top-left corner of the screen.
    """
    x_pixel = 0
    y_pixel = 0
    _crossline = INIT_CROSSLINE # draw crossline?

    def __init__(self):
        """Constructs simple geospace canvas."""
        gtk.Fixed.__init__(self)
        self.set_has_window(True)
        self.set_events(gtk.gdk.ENTER_NOTIFY | gtk.gdk.ENTER_NOTIFY_MASK | \
                        gtk.gdk.LEAVE_NOTIFY | gtk.gdk.LEAVE_NOTIFY_MASK | \
                        gtk.gdk.POINTER_MOTION_HINT_MASK | \
                        gtk.gdk.POINTER_MOTION_MASK)

        self.connect("enter_notify_event", self.mouse_to_cross_cb)
        self.connect("leave_notify_event", self.mouse_to_pointer_cb)
        self.connect("motion_notify_event", self.motion_notify_cb)

        self.x_label = gtk.Label()
        self.y_label = gtk.Label()
        self.area = gtk.DrawingArea()

        self.put(self.x_label, 100, 300)
        self.put(self.y_label, 12, 40)
        self.put(self.area, 0, 0)

        self.redraw_timeout = False
        self.current_bbox = BoundingBox(None, None, None, None)

    def mouse_to_cross_cb(self, area, args):
        """Changes the cursor to a crosshair."""
        self._change_cursor(CROSS_CURSOR)

    def mouse_to_pointer_cb(self, area, args):
        """Changes the cursor to an arrow."""
        self._change_cursor(ARROW_CURSOR)

    def _change_cursor(self, gdk_cursor):
        """Changes the parent_windows Cursor to the given one.

         @param gdk_cursor: The cursor.
        """
        self.get_parent_window().set_cursor(gdk_cursor)

    def get_map_coords(self):
        """Returns the cursors coordinates of the specified geospace instance.

        @return: A tuple of coordinates specific to the used CRS.
        @note: Has to be implemented in a subclass which serves as the concrete
        geospace like a georeferenced raster map. Amore complex example would
        be an HTML viewer which serves as the server side representation of a
        javascript client running some map API like openlayers, yahoo or google.
        """
        raise NotImplementedError

    def register_toolbars(self, toolbox):
        """Registers all toolbars the view provides.

        @param toolbox: The activities toolbox.
        @note: Has to be implemented in a subclass to give the user tools at
        hand to work with the view.
        """
        raise NotImplementedError

    def motion_notify_cb(self, widget, event):
        """Sets the pointers screen-coordinates (y starting from top).

        If the user toggled to show the _crossline it will be drawn here.
        """
        self.x_pixel, self.y_pixel = event.get_coords()
        if self._crossline:
            x_coord, y_coord = self.get_map_coords()
            self.x_label.set_text('(x=%s)' % str(x_coord))

            alloc = widget.get_allocation()
            self.y_label.set_text('(y=%s)' % str(y_coord))
            x_label_width = self.x_label.allocation.width
            y_label_width = self.y_label.allocation.width
            x_label_height = self.x_label.allocation.height
            y_label_height = self.y_label.allocation.height

            # find best placement of labels
            x_x_label = -1
            y_x_label = -1
            x_y_label = -1
            y_y_label = -1
            if x_coord > alloc.width/2:
                x_x_label = 0
            else:
                x_x_label = alloc.width - x_label_width
            if y_coord > alloc.height/2:
                y_x_label = y_coord - x_label_height
            else:
                y_x_label = y_coord + 2
            if y_coord > alloc.height/2:
                y_y_label = 0
            else:
                y_y_label = alloc.height - y_label_height
            if x_coord > alloc.width/2:
                x_y_label = x_coord - y_label_width - 2
            else:
                x_y_label = x_coord + 2

            widget.move(self.x_label, x_x_label, y_x_label)
            widget.move(self.y_label, x_y_label, y_y_label)

            drawable = widget.window
            self.draw_crosslines(drawable, alloc, x_coord, y_coord)
            if self.redraw_timeout:
                gobject.source_remove(self.redraw_timeout)
            self.redraw_timeout = gobject.timeout_add(50,  \
                                                      self.draw_crosslines, \
                                                      drawable, alloc, \
                                                      self.x_pixel, \
                                                      self.y_pixel)

    def draw_crosslines(self, drawable, alloc, x_pixel, y_pixel):
        """Draws a line with the given parameters."""
        ctx = drawable.new_gc()
        ctx.set_line_attributes(1,  gtk.gdk.LINE_SOLID, gtk.gdk.CAP_BUTT, \
                                gtk.gdk.JOIN_ROUND)
        drawable.draw_line(ctx, x_pixel, 0, x_pixel, alloc.height)
        drawable.draw_line(ctx, 0, y_pixel, alloc.width, y_pixel)

    def switch_y(self):
        """Switches the mouse-pointers current y-coordinate so that the
        coordinate system is mathematical instead of a screen coordinate system.

        @return: The y-coordinate starting from bottom instead from top.
        """
        return self.get_allocation().height - self.y_coord

    def toggle_crossline_cb(self, button):
        """Serves as callback to toggle show-crosslines status.

        @note: Pass method to GeospaceToolbar#enable_toggle_crosslines
        """
        if self._crossline:
            self.x_label.hide()
            self.y_label.hide()
        else:
            self.x_label.set_text('')
            self.y_label.set_text('')
            self.x_label.show()
            self.y_label.show()
        self._crossline = not self._crossline
        self.queue_draw()

###############################################################################

class GeospaceToolbar(gtk.Toolbar):
    """Tools which interacts with the currently chosen view.

    This toolbar is meant general: General map tools can be enabled. The
    toolbar serves as controller. Because you use a specific geospace you have
    to wire specific functionality to the common tools offered by this toolbar.

    Tools you may want to enable:
    ===========     ==========================
    toggle_crosslines      User wants to show crosslines.

    navigation                User wants to navigate the map. Includes
                                    buttons for NESW.

    zoom-in                   User wants to zoom-in the current map view.

    zoom-out                  User wants to zoom-out the current map view.

    zoom-bestfit              User wants to zoom-in the current map view.
    ===========     ==========================

    Enable one of these tools by calling the appropriate method with your
    custom callback method before adding the toolbar to the toolbox.
    """
    title = _('Map tools')

    def __init__(self, name=None):
        """Creates general toolbar where general map tools can be enabled.

        @param name: The name of the toolbar.
        """
        gtk.Toolbar.__init__(self)
        if name:
            self.name = name

    def enable_toggle_crosslines(self, on_toggle_crosslines):
        """Enables tool to toggle crosslines.

        @param on_toggle_crosslines: The callback function setting if the
        crossline shall be drawn or not.
        """
        toggle_crossline_btn = ToggleToolButton('toggle-crosslines')
        toggle_crossline_btn.set_tooltip(_('Show crossline.'))
        toggle_crossline_btn.set_active(INIT_CROSSLINE)
        toggle_crossline_btn.connect('clicked', on_toggle_crosslines)
        toggle_crossline_btn.show()
        self.insert(toggle_crossline_btn, -1)

    def enable_zoom_in(self, on_zoom_in):
        """Enables zoom-in support on this toolbar.

        @param on_zoom_in: The callback function to be called when user wants
        to zoom in.
        """
        zoom_in_btn = ToolButton('zoom-in')
        zoom_in_btn.set_tooltip(_('Zoom in.'))
        zoom_in_btn.connect('clicked', on_zoom_in)
        zoom_in_btn.show()
        self.insert(zoom_in_btn, -1)

    def enable_zoom_out(self, on_zoom_out):
        """Enables zoom-ou support on this toolbar.

        @param on_zoom_out: The callback function to be called when user wants
        to zoom ou.
        """
        zoom_out_btn = ToolButton('zoom-out')
        zoom_out_btn.set_tooltip(_('Zoom out.'))
        zoom_out_btn.connect('clicked', on_zoom_out)
        zoom_out_btn.show()
        self.insert(zoom_out_btn, -1)

    def enable_zoom_bestfit(self, on_zoom_bestfit):
        """Enables zoom-to-best-fit support on this toolbar.

        @param on_zoom_bestfit: The callback function to be called when user
        wants to zoom to best extent.
        """
        zoom_best_fit_btn = ToolButton('zoom-best-fit')
        zoom_best_fit_btn.set_tooltip(_('Zoom best fitting extent.'))
        zoom_best_fit_btn.connect('clicked', on_zoom_bestfit)
        zoom_best_fit_btn.show()
        self.insert(zoom_best_fit_btn, -1)

    def enable_navigation(self, nav_callbacks):
        """Enables tools to navigate the map via buttons.

        @param nav_callbacksna: A tuple which contains exactly 4 callbacks:
                ===========  =============
                nav_callbacks[0]   A callback to step west

                nav_callbacks[1]   A callback to step north

                nav_callbacks[2]   A callback to step south

                nav_callbacks[3]   A callback to step east
                ===========  =============
        @raise ValueError: if tuple does not contain exact 4 elements.
        """
        if len(nav_callbacks) != 4:
            raise ValueError, 'nav_callbacks must contain exact 4 callbacks!'
        else:
            self._enable_step_west(nav_callbacks[0])
            self._enable_step_north(nav_callbacks[1])
            self._enable_step_south(nav_callbacks[2])
            self._enable_step_east(nav_callbacks[3])

    def _enable_step_north(self, on_step_north):
        """Enables button to step north.

        @param on_step_north: The callback function to be called when the user
        wants to step north.
        """
        step_north_btn = ToolButton('step-north')
        step_north_btn.set_tooltip(_('Move north.'))
        step_north_btn.connect('clicked', on_step_north)
        step_north_btn.show()
        self.insert(step_north_btn, -1)

    def _enable_step_east(self, on_step_east):
        """Enables button to step east.

        @param on_step_east: The callback function to be called when the user
        wants to step east.
        """
        step_east_btn = ToolButton('step-east')
        step_east_btn.set_tooltip(_('Move east.'))
        step_east_btn.connect('clicked', on_step_east)
        step_east_btn.show()
        self.insert(step_east_btn, -1)

    def _enable_step_south(self, on_step_south):
        """Enables button to step south.

        @param on_step_south: The callback function to be called when the user
        wants to step south.
        """
        step_south_btn = ToolButton('step-south')
        step_south_btn.set_tooltip(_('Move south.'))
        step_south_btn.connect('clicked', on_step_south)
        step_south_btn.show()
        self.insert(step_south_btn, -1)

    def _enable_step_west(self, on_step_west):
        """Enables button to step west.

        @param on_step_west: The callback function to be called when the user
        wants to step west.
        """
        step_west_btn = ToolButton('step-west')
        step_west_btn.set_tooltip(_('Move west.'))
        step_west_btn.connect('clicked', on_step_west)
        step_west_btn.show()
        self.insert(step_west_btn, -1)

###############################################################################

class BoundingBox():
    """Represents the spatial extent of a feature as a rectangle.

    Axis ordering is lon/lat, although coordinates refer to EPSG:4326 CRS.

    (lon_min, lat_min, lon_max, lat_max) == (None, None, None, None) is meant
    to cover the maximum extent possible. This means the extent of the context
    the boundingbox is in, which doesn't necessarily mean [-180, -90, 180, 90].
    """

    STEP_FACTOR = 10 # percent of boundingbox height/width

    def __init__(self, lon_min, lat_min, lon_max, lat_max):
        """Creates boundingbox with corner coordinates.

        If all parameters are None, the instance shall be interpreted to cover
        the biggest extent possible.

        @note: All values expected to be in EPSG:4326.
        @param lon_min: The longitude of lower left.
        @param lat_min: The latitude of lower left.
        @param lon_max: The longitude of upper right.
        @param lat_max: The latitude of upper right.
        """
        self.lon_min = lon_min
        self.lat_min = lat_min
        self.lon_max = lon_max
        self.lat_max = lat_max

    def covers_max_extent(self):
        """Indicates if boundingbox shall cover maximum extent possible."""
        return self.lon_min is None or \
               self.lon_max is None or \
               self.lat_min is None or \
               self.lat_max is None

    def reset(self):
        """Resets the BoundingBox.

        Instance is reset to BoundingBox(None, None, None, None) which is meant
        to cover maximum extent possible.

        @note: This does not mean [-180, -90, 180, 90]! The boundingbox shall
        cover the biggest extent of the context in which it is used (e.g. in a
        WMS GetMap request it will cover the biggest extent of the layers which
        shall be displayed.)
        """
        self.lon_min = None
        self.lat_min = None
        self.lon_max = None
        self.lat_max = None

    def get_center(self):
        """Returns center (lon/lat) of boundingbox instance."""
        if not self.covers_max_extent():
            return self.get_width() / 2.0 , self.get_height() / 2.0

    def move_west(self):
        """Moves the boundingbox west according to the STEP_FACTOR."""
        if not self.covers_max_extent():
            bbox_width = self.get_width()
            self.lon_min -= bbox_width/100 * self.STEP_FACTOR
            self.lon_max -= bbox_width/100 * self.STEP_FACTOR

    def move_north(self):
        """Moves the boundingbox north according to the STEP_FACTOR."""
        if not self.covers_max_extent():
            bbox_height = self.get_height()
            self.lat_min += bbox_height/100 * self.STEP_FACTOR
            self.lat_max += bbox_height/100 * self.STEP_FACTOR

    def move_south(self):
        """Moves the boundingbox south according to the STEP_FACTOR."""
        if not self.covers_max_extent():
            bbox_height = self.get_height()
            self.lat_min -= bbox_height/100 * self.STEP_FACTOR
            self.lat_max -= bbox_height/100 * self.STEP_FACTOR

    def move_east(self):
        """Moves the boundingbox east according to the STEP_FACTOR."""
        if not self.covers_max_extent():
            bbox_width = self.get_width()
            self.lon_min += bbox_width/100 * self.STEP_FACTOR
            self.lon_max += bbox_width/100 * self.STEP_FACTOR

    def zoom_in(self):
        """Zooms into the boundingboxto the STEP_FACTOR."""

    def zoom_out(self):
        """Zooms out the boundingboxto the STEP_FACTOR."""

    def merge_bbox(self, bbox):
        """Extends the boundingbox instance with the given bbox parameter.

        @param bbox: The boundingbox, this instance shall contain
        """
        if bbox is None:
            return
        if self.covers_max_extent():
            self.lon_min = bbox.lon_min
            self.lat_min = bbox.lat_min
            self.lon_max = bbox.lon_max
            self.lat_max = bbox.lat_max

        #LOGGER.debug('Merge bboxes %s and %s' % (self, bbox))
        if (self.lon_min + 200) > (bbox.lon_min + 200):
            self.lon_min = bbox.lon_min
        if (self.lat_min + 200) > (bbox.lat_min + 200):
            self.lat_min = bbox.lat_min
        if (self.lon_max + 200) < (bbox.lon_max + 200):
            self.lon_max = bbox.lon_max
        if (self.lat_max + 200) < (bbox.lat_max + 200):
            self.lat_max = bbox.lat_max

    def tuple(self):
        """Returns the values as unchangable tlon_minuple."""
        return (self.lon_min, self.lat_min, self.lon_max, self.lat_max)

    def get_width(self):
        """Returns the width of this instance."""
        return self.lon_max - self.lon_min

    def get_height(self):
        """Returns the height of this instance."""
        return self.lat_max - self.lat_min

    def get_ratio(self):
        """Returns the ratio (height/width) of this instance."""
        return self.get_height()/self.get_width()

    def __get__(self):
        return [self.lon_min, self.lat_min, self.lon_max, self.lat_max]

    def __str__(self):
        """Returns string representation of the instances values."""
        return str((self.lon_min, self.lat_min, self.lon_max, self.lat_max))
