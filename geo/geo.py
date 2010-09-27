"""
Module defining the general geo classes and functionality.
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
__version__ = '$Id: geo.py 179 2010-09-27 08:47:24Z  $'

import os
import gtk
import gobject
import logging

from sugar.graphics.toolbutton import ToolButton
from sugar.graphics.toggletoolbutton import ToggleToolButton
from sugar.graphics.radiotoolbutton import RadioToolButton

import utils
import constants
import geomodel

from utils import _
from shapely.geometry import Point
from shapely.geometry import Polygon

# constants
INIT_CROSSLINE = False
INIT_CENTER_MAP = False

CROSS_CURSOR = gtk.gdk.Cursor(gtk.gdk.CROSSHAIR)
ARROW_CURSOR = gtk.gdk.Cursor(gtk.gdk.ARROW)
WAIT_CURSOR = gtk.gdk.Cursor(gtk.gdk.WATCH)
PAN_CURSOR = gtk.gdk.Cursor(gtk.gdk.FLEUR)
_LABEL_X = gtk.Label()
_LABEL_Y = gtk.Label()
_STATUS_TEXT = gtk.Label()
BTN_ICON_SIZE = (40,40)
ICON_SIZE = (30,30)

###############################################################################

class GeoCanvas(gtk.HBox):
    """
    Serves as basic space which observes the current mouse position.

    The general GeoCanvas has no knowledge of the concrete CRS which is
    being used (within RasterView or WMSView). The canvas CRS is the standard
    screen system which has its origin on the top-left corner of the screen.

    connect to signals:
        model.connect('position_changed', model)
    """

    __gsignals__ = {'position_changed': (gobject.SIGNAL_RUN_LAST,
                                         gobject.TYPE_NONE,
                                         (gobject. TYPE_PYOBJECT,))
         }

    # toggle booleans
    _CROSSLINES = INIT_CROSSLINE
    _CENTER_MAP = INIT_CENTER_MAP
    _SHOW_ALL_POSITIONS = False # if false, only the own position is shown

    _DRAW_NO_POSITION = 0
    _DRAW_OWN_POSITION = 1
    _DRAW_ALL_POSITIONS = 2

    draw_mode = _DRAW_OWN_POSITION
    drawn_players = { } # { player.nickname : icon }

    x_pixel = 0
    y_pixel = 0

    def __init__(self, activity):
        """
        Constructs simple geo canvas.
        """
        gtk.HBox.__init__(self)
        self._logger = logging.getLogger('geo.GeoCanvas')
        self._logger.setLevel(constants.LOG_LEVEL)

        self.activity = activity
        self.activity.connect("position_changed", self.on_position_changed)

        self.fixed = gtk.Fixed()
        self.canvas = gtk.EventBox()
        self.canvas.connect("leave_notify_event", self.cursor_to_pointer_cb)
        self.canvas.connect("enter_notify_event", self.cursor_to_cross_cb)
        self.canvas.add_events(gtk.gdk.ENTER_NOTIFY |
                               gtk.gdk.ENTER_NOTIFY_MASK | \
                               gtk.gdk.LEAVE_NOTIFY |
                               gtk.gdk.LEAVE_NOTIFY_MASK)

        self.drawable = DrawingCanvas(self)
        self.fixed.put(self.drawable, 0, 0)
        self.canvas.add(self.fixed)
        self.fixed.show()

        self.connect("motion_notify_event", self.mouse_motion_cb)
        self.canvas.add_events(gtk.gdk.POINTER_MOTION_MASK | \
                               gtk.gdk.POINTER_MOTION_HINT_MASK)

        separator1 = gtk.SeparatorToolItem()
#        separator1.set_draw(True)
        #separator1.set_expand(True)
        separator2 = gtk.SeparatorToolItem()
#        separator2.set_draw(True)
        #separator2.set_expand(True)
        separator3 = gtk.SeparatorToolItem()
        separator3.set_draw(False)
#        separator3.set_expand(True)
        _STATUS_TEXT.set_size_request(620, 20)

        self.status_bar = gtk.HBox()
        self.status_bar.pack_start(_STATUS_TEXT)
        self.status_bar.pack_start(separator1)
        self.status_bar.pack_start(_LABEL_X)
        self.status_bar.pack_start(separator2)
        self.status_bar.pack_start(_LABEL_Y)
        self.status_bar.pack_start(separator3)

        self.current_bbox = BoundingBox(None, None, None, None)
        self.crosslines_timeout = False

        self.vbox = gtk.VBox()
        self.vbox.pack_start(self.canvas)
        self.vbox.pack_end(self.status_bar)

        self.pack_start(self.vbox)
        self.show_all()

        self.redraw_players = None

    def init_center(self, activity, position):
        """
        Override if the framework shall be able to center the map extent on
        the current position with maximum zoom.
        """
        pass

    def cursor_to_cross_cb(self, widget, event):
        """
        Changes the cursor to a crosshair.
        """
        self.change_cursor(CROSS_CURSOR)

    def cursor_to_pointer_cb(self, widget, event):
        """
        Changes the cursor to an arrow.
        """
        self.change_cursor(ARROW_CURSOR)

    def change_cursor(self, gdk_cursor):
        """
        Changes the parent_windows Cursor to the given one.

        @param gdk_cursor: The cursor.
        """
        self.get_parent_window().set_cursor(gdk_cursor)

    def expose_canvas_cb(self, widget, event):
        self._logger.debug("expose_canvas_cb()")
        x, y, width, height = event.area
        self.queue_draw_area(x, y, width, height)
#        drawable = widget.window
#        if GeoCanvas._CROSSLINES:
#            self.draw_crosslines(drawable, self.x_pixel, self.y_pixel)

    def mouse_motion_cb(self, widget, event):
        """
        Sets the pointers screen-coordinates (y starting from top).

        If the user toggled to show the crossline it will be drawn here.
        """
        if event.is_hint:
            x, y, state = self.window.get_pointer()
        else:
            x = event.x
            y = event.y
            state = event.state
        #self._logger.debug("x: %s, y: %s, state: %s", x, y, state)

        self.x_pixel = int(event.get_coords()[0])
        self.y_pixel = int(event.get_coords()[1])

        cursor_world = self.get_world_cursor()
        cursor_lon = cursor_world.x
        cursor_lat = cursor_world.y

        phi = u"\u03D5"
        lamda = u"\u019B"

        _LABEL_X.set_text('lon (%s): %.5f' % (lamda, cursor_lon))
        _LABEL_Y.set_text('lat (%s): %.5f' % (phi, cursor_lat))

        self.motion_crosslines(widget)

    def motion_crosslines(self, widget):

        pass
#        if GeoCanvas._CROSSLINES:
#
#            if self.current_bbox.is_empty():
#                return

#            drawable = self.drawable.window
#            self.draw_crosslines(drawable, self.x_pixel, self.y_pixel)

#            cursor_world = self.get_world_cursor()
#            cursor_lon = cursor_world.x
#            cursor_lat = cursor_world.y
#            _LABEL_X.set_text('(lon=%1.5f)' % cursor_lon)
#            _LABEL_Y.set_text('(lat=%1.5f)' % cursor_lat)
#
#            y_label_width = _LABEL_Y.allocation.width
#            x_label_width = _LABEL_X.allocation.width
#            y_label_height = _LABEL_Y.allocation.height
#            x_label_height = _LABEL_X.allocation.height
#
#            x_x_label = -1
#            y_x_label = -1
#            x_y_label = -1
#            y_y_label = -1
#
#            # find best placement of labels
#            alloc = self.get_allocation()
#            if self.x_pixel > alloc.width/2:
#                x_y_label = 0
#            else:
#                x_y_label = alloc.width - y_label_width - 5
#            if self.x_pixel > alloc.width/2:
#                x_x_label = self.x_pixel - x_label_width - 5
#            else:
#                x_x_label = self.x_pixel + 5
#            if self.y_pixel > alloc.height/2:
#                y_y_label = self.y_pixel - y_label_height - 5
#            else:
#                y_y_label = self.y_pixel + 5
#
#            if self.y_pixel > alloc.height/2:
#                y_x_label = 0
#            else:
#                y_x_label = alloc.height - x_label_height - 5
#
#            self.fixed.move(_LABEL_Y, int(x_y_label), int(y_y_label))
#            self.fixed.move(_LABEL_X, int(x_x_label), int(y_x_label))

            # drawing crosslines need a delay
#            if self.crosslines_timeout:
#                gobject.source_remove(self.crosslines_timeout)
#            self.crosslines_timeout = gobject.timeout_add(100,
#                                                      self.draw_crosslines, \
#                                                      drawable,
#                                                      self.x_pixel,
#                                                      self.y_pixel)
#
#    def draw_crosslines(self, drawable, x_pixel, y_pixel):
#        """
#        Draws a line with the given parameters.
#        """
#        #self._logger.debug('draw_crosslines()')
#        alloc = self.drawable.get_allocation()
#        ctx = drawable.new_gc()
#        ctx.set_line_attributes(1, gtk.gdk.LINE_SOLID, \
#                                gtk.gdk.CAP_BUTT, \
#                                gtk.gdk.JOIN_ROUND)
#        drawable.draw_line(ctx, x_pixel, 0, x_pixel, alloc.height)
#        drawable.draw_line(ctx, 0, y_pixel, alloc.width, y_pixel)
#        return False

    def toggle_crossline_cb(self, button):
        """
        Callback for toggling show-crosslines status.

        @note: Pass as callback to GeoToolbar#enable_toggle_crosslines
        """
#        if GeoCanvas._CROSSLINES:
#            _LABEL_X.hide()
#            _LABEL_Y.hide()
#        else:
#            _LABEL_X.show()
#            _LABEL_Y.show()

        GeoCanvas._CROSSLINES = not GeoCanvas._CROSSLINES
        self._logger.debug("Crosslines toggled: %s", GeoCanvas._CROSSLINES)
#        self.canvas.queue_draw()

    def _enable_timeout_redraw_players(self):
        """
        Starts timeout interval to redraw players participating the game.

        We use our own draw interval, since many players and an awkward
        interval could lead to a neverending redraw (each player renews
        her position in a 3 sec interval .. when 10 players are active,
        this could lead to a "bad" update rate of 0.3 sec)
        """
#        self._logger.debug("_enable_timeout_redraw_players()")
        self.redraw_players = gobject.timeout_add(1000, self.redraw_drawn_players)

    def _disable_timeout_redraw_players(self):
        """
        Disables timeout for redrawing players on map from gobject main loop.
        """
#        self._logger.debug("_disable_timeout_redraw_players()")
        if self.redraw_players:
            gobject.source_remove(self.redraw_players)
            self.redraw_players = None

    def _draw_own_player_on_map(self):
        """
        Draws the own player on the map. The player will be drawn in its
        individual colors. The icon will be cached within L{geomodel}.
        """
        nickname = self.activity.get_model().mynickname
        self._draw_player_on_map(nickname)

    def _draw_all_players_on_map(self):
        """
        Draws all players participating the game on the map (only, if the
        player has moved). Each player will be drawn in its individual colors.
        The icons will be cached within L{geomodel}.
        """
        model = self.activity.get_model()
        for key in model.players.keys():
            player = model.players[key]
            self._draw_player_on_map(player.nickname)
#        self._logger.debug("all players drawn on the map.")

    def _draw_no_players_on_map(self):
        """
        Removes the all players from the map and also the timeout from
        gobject main loop.

        @note: This method stops redrawing timeout (if there is one). Re-enable
        it if necessary after this method returns.
        @see: L{geo.Geo._enable_timeout_redraw_players}
        """
#        self._logger.debug("_draw_no_players_on_map()")
        model = self.activity.get_model()
        self._disable_timeout_redraw_players() # stop redrawing
        for icon in self.drawn_players.values():
            self._logger.debug("remove icon: %s", icon)
            self.drawable.remove_overlay(icon)
        self.drawn_players.clear()

    def _draw_player_on_map(self, name):
        """
        Draws the player on the map. The player will be drawn in its
        individual colors. The icon will be cached via L{geomodel}.

        @param name: the nickname of the player to be drawn.
        """
#        self._logger.debug("_draw_player_on_map(): %s", name)
        model = self.activity.get_model()
        player = model.players[name]
        position = player.position

        if name in self.drawn_players.keys():
            self.drawable.redraw_overlay(self.drawn_players[name], position)
        else:
            self._logger.debug("draw new icon")
            self.drawn_players[name] = player.get_icon()
            self.drawable.draw_overlay(self.drawn_players[name], position)

    def radio_show_no_positions_cb(self, button):
        """
        Callback to remove all drawn players from the map and stops redraw
        timeout from the view.
        """
#        self._logger.debug("radio_show_no_positions")
        if button.get_active():
            self._draw_no_players_on_map() # clear map
            self._disable_timeout_redraw_players()
            self.draw_mode = self._DRAW_NO_POSITION

    def radio_show_own_position_cb(self, button):
        """
        Callback to toggle showing only the own position status.
        """
#        self._logger.debug("radio_show_own_position_cb()")
        if button.get_active():
            self._draw_no_players_on_map() # clear map
            self._draw_own_player_on_map()
            self.draw_mode = self._DRAW_OWN_POSITION

            # (re-)enable redraw mode
            if self.redraw_players is None:
                self._enable_timeout_redraw_players()

    def radio_show_all_position_cb(self, button):
        """
        Callback, toggling the display of all players.
        """
#        self._logger.debug("radio_show_all_position_cb()")
        if button.get_active():
            self._draw_no_players_on_map() # avoid doubles
            self._draw_all_players_on_map()
            self.draw_mode = self._DRAW_ALL_POSITIONS

            # (re-)enable redraw mode
            if self.redraw_players is None:
                self._enable_timeout_redraw_players()

    def redraw_drawn_players(self):
        """
        Callback method called from gobject main loop every xx seconds.
        Redraws all players which are currently displayed and participating
        the game.

        @return: True, so method can be used as a timeout callback, so the
        movement of each player will be visible.
        """
#        self._logger.debug("_redraw_drawn_players()")

        if self.draw_mode == self._DRAW_OWN_POSITION:
            self._draw_own_player_on_map()
        elif self.draw_mode == self._DRAW_ALL_POSITIONS:
            self._draw_all_players_on_map()
        elif self.draw_mode == self._DRAW_NO_POSITION:
            self._draw_no_players_on_map()

        return True # enable loop

    ######################## ABSTRACT/VIRTUAL METHODS #########################

    def get_world_cursor(self):
        """
        Returns the cursors coordinates for the specified geo instance.

        @return: A tuple (lon,lat) of geographic WGS84 coordinates.
        """
        raise NotImplementedError

    def get_screen_coords(self, pos):
        """
        Returns the cursors screen coordinates for the given coordinates.

        @param pos: The position data in lon/lat.
        @return: A tuple (x,y) representing the given lon/lat coordiantes.
        """
        raise NotImplementedError

    def register_toolbars(self, toolbox):
        """
        Registers all toolbars the view provides.

        @param toolbox: The activities toolbox.
        @note: Has to be implemented in a subclass to give the user tools at
        hand to work with the view.
        """
        raise NotImplementedError

    def on_position_changed(self, activity, position):
        """
        Callback method to be implemented when position has changed.
        """
        pass

###############################################################################

class DrawingCanvas(gtk.DrawingArea):
    """
    The DrawingCanvas provides the central canvas for drawing things (map,
    icons, etc.).
    """

    overlays = dict() # { overlay : Point }
    buddies = dict() # { name : (icon, position) }
    pixmap = None
    ctx = None

    def __init__(self, canvas):
        gtk.DrawingArea.__init__(self)
        self._logger = logging.getLogger('DrawingCanvas')
        self._logger.setLevel(constants.LOG_LEVEL)

        self.connect("configure_event", self.configure_cb)
        self.connect("expose_event", self.expose_cb)

        self.canvas = canvas

    def configure_cb(self, widget, event):
        """
        Configures the DrawingCanvas: Creates and draws its pixmap.
        """
#        self._logger.debug('configure_cb()')

        if self.flags() & gtk.REALIZED:
            x, y, w, h = self.canvas.fixed.get_allocation()
            self.set_size_request(w, h)
            drawable = widget.window
            self.ctx = drawable.new_gc()
            x, y, width, height = widget.get_allocation()
            self.pixmap = gtk.gdk.Pixmap(drawable, w, h)

            #self._logger.debug('draw pixmap on canvas: %s %s %s %s', x, y, w, h)
            #drawable.draw_drawable(self.ctx, self.pixmap, x, y, x, y, w, h)

    def expose_cb(self, widget, event):
        if self.pixmap:
            x, y, w, h = event.area
#            self._logger.debug('expose_cb(): area %s, %s, %s, %s', x, y, w, h)
#            self._logger.debug('expose source: %s', type(widget))

            drawable = widget.window
            drawable.draw_drawable(self.ctx, self.pixmap, x, y, x, y, w, h)
            for overlay in self.overlays.keys():
                self.draw_overlay(overlay, self.overlays[overlay])
        else:
            self._logger.info("expose(): no pixmap to draw on!")

    def draw_map(self, pixbuf, x_pos, y_pos):
        """
        Draws map/map-tile at the specified screen coordinate.
        """
#        self._logger.debug("draw_map()")
        self.pixmap.draw_pixbuf(self.ctx, pixbuf, 0, 0, x_pos, y_pos)

    def draw_overlay(self, overlay, pos):
        """
        Draws the given xo icon on the map at the given pixel position.
        """
#        self._logger.debug('draw_overlay()')
        self.overlays[overlay] = pos
        position = self.canvas.get_screen_coords(pos)
        if not position:
            # beyond spatial extent
            return
        x_rel, y_rel, width, height, x_pos, y_pos = self._get_draw_details(overlay, position)
        #self._logger.debug('relx: %s, rely: %s', x_rel, y_rel)
        if self.window:
            self.window.draw_pixbuf(self.ctx, overlay, 0, 0, x_pos, y_pos)

    def _get_draw_details(self, overlay, position):
        """
        Convenience method to get drawing details for an overlay.
        """
        x_rel, y_rel = position
        width = overlay.get_width()
        height = overlay.get_height()
        x_offset = width / 2
        y_offset = height / 2
        x_pos = x_rel - y_offset
        y_pos = y_rel - y_offset

        return x_rel, y_rel, width, height, x_pos, y_pos

    def redraw_overlay(self, overlay, pos):
        """
        Redraws the given overlay on a new position.

        @param overlay: The pre-existing overlay to redraw.
        @param pos: the new position of the overlay.
        """
#        self._logger.debug('draw_overlay()')
        if overlay in self.overlays.keys():
            # first remove for correct drawing
            self.remove_overlay(overlay)
            #pass
        self.overlays[overlay] = pos
        position = self.canvas.get_screen_coords(pos)
        if not position:
            # beyond spatial extent
            return
        x_rel, y_rel, width, height, x_pos, y_pos = self._get_draw_details(overlay, position)
        #self._logger.debug('relx: %s, rely: %s', x_rel, y_rel)
        if self.window:
            self.window.draw_pixbuf(self.ctx, overlay, 0, 0, x_pos, y_pos)
            self.queue_draw_area(x_pos, y_pos, width, height)

    def remove_overlay(self, overlay):
        """
        Removes an overlay from the map.
        """
#        self._logger.debug("remove_overlays()")
#        self._logger.debug("drawn overlays %s", self.overlays)
        if overlay in self.overlays:
            position = self.overlays[overlay]
            pos = self.canvas.get_screen_coords(position)
            if not pos:
                # beyond spatial extent
                del self.overlays[overlay]
                return
            x_rel, y_rel, width, height, x_pos, y_pos = self._get_draw_details(overlay, pos)
            width = overlay.get_width()
            height = overlay.get_height()
            del self.overlays[overlay]
            #self._logger.debug('x: %s, y: %s, w: %s, h: %s', x_pos, y_pos, width, height)
            self.queue_draw_area(x_pos, y_pos, width, height)
#            self._logger.debug('overlay deleted')

###############################################################################

class GeoToolbar(gtk.Toolbar):
    """
    Tools which interacts with the currently chosen view.

    This toolbar is meant general: General map tools can be enabled. The
    toolbar serves as controller. Because you use a specific geo you have
    to wire specific functionality to the common tools offered by this toolbar.

    Tools you may want to enable:
    ===========     ==========================
    enable_goto_current_position
                                   User wants to center map over current
                                   position.

    toggle_crosslines
                                   User wants to show crosslines.

    navigation
                                   User wants to navigate the map. Includes
                                   buttons for NESW.

    zoom-in
                                   User wants to zoom-in the current map view.

    zoom-out
                                   User wants to zoom-out the current map view.

    zoom-bestfit
                                   User wants to zoom-in the current map view.
    ===========     ==========================

    Enable one of these tools by calling the appropriate method with your
    custom callback method before adding the toolbar to the toolbox.
    """
    title = _('Map tools')
    radio_show_own_pos_btn = None
    radio_show_all_pos_btn = None

    def __init__(self, view, name=None):
        """
        Creates general toolbar where general map tools can be enabled.

        @param name: The name of the toolbar.
        """
        gtk.Toolbar.__init__(self)
        self.set_property('can-focus', False)
        self.view = view
        if name:
            self.name = name
            self._logger = logging.getLogger(name)
        else:
            self._logger = logging.getLogger('geo.GeoToolbar')
        self._logger.setLevel(constants.LOG_LEVEL)

        # remove predefined key bindings
        gtk.binding_entry_remove(self, gtk.keysyms.Left, 0)
        gtk.binding_entry_remove(self, gtk.keysyms.Right, 0)
        gtk.binding_entry_remove(self, gtk.keysyms.Up, 0)
        gtk.binding_entry_remove(self, gtk.keysyms.Down, 0)
        gtk.binding_entry_remove(self, gtk.keysyms.plus, 0)
        gtk.binding_entry_remove(self, gtk.keysyms.minus, 0)

        self.callbacks = {}
        self.connect('key-press-event', self.key_pressed_cb, self.callbacks)

        self.show_no_positions = RadioToolButton()
        icon_name = os.path.join(constants.ICON_PATH, "show-no-positions.svg")
        icon = utils.load_svg_image(icon_name, None, None, BTN_ICON_SIZE)
        img = gtk.image_new_from_pixbuf(icon)
        self.show_no_positions.set_icon_widget(img)
        self.show_no_positions.set_tooltip(_('Show no players.'))

    def enable_show_own_position(self, view):
        """
        Shows the only the own position on the map.
        """
        self.radio_show_own_pos_btn = RadioToolButton(group=self.show_no_positions)
        (fill, stroke) = ('#ffffff', '#000000') # black/white explicit
        buddy_icon = utils.get_xo_icon(stroke, fill, BTN_ICON_SIZE)
        img = gtk.image_new_from_pixbuf(buddy_icon)
        self.radio_show_own_pos_btn.set_icon_widget(img)
        self.radio_show_own_pos_btn.set_tooltip(_('Show only me.'))
        self.radio_show_own_pos_btn.connect('clicked', view.radio_show_own_position_cb)
        self.insert(self.radio_show_own_pos_btn, -1)
        self.radio_show_own_pos_btn.show_all()
        if self.radio_show_all_pos_btn:
            self.show_no_positions.connect("clicked", view.radio_show_no_positions_cb)
            self.show_no_positions.show_all()
            self.insert(self.show_no_positions, -1)

    def enable_show_all_positions(self, view):
        """
        Shows the position of all players participating the game.
        """
        self.radio_show_all_pos_btn = RadioToolButton(group=self.show_no_positions)
        icon_name = os.path.join(constants.ICON_PATH , 'show-all-players.svg')
        icon = utils.load_svg_image(icon_name, None, None, BTN_ICON_SIZE)
        img = gtk.image_new_from_pixbuf(icon)
        self.radio_show_all_pos_btn.set_icon_widget(img)
        self.radio_show_all_pos_btn.set_tooltip(_('Show all players.'))
        self.radio_show_all_pos_btn.connect('clicked', view.radio_show_all_position_cb)
        self.insert(self.radio_show_all_pos_btn, -1)
        self.radio_show_all_pos_btn.show_all()
        if self.radio_show_own_pos_btn:
            self.show_no_positions.connect("clicked", view.radio_show_no_positions_cb)
            self.show_no_positions.show_all()
            self.insert(self.show_no_positions, -1)
            self.radio_show_all_pos_btn.set_active(True)

    def enable_center_current_position(self, on_center_on_current_position):
        """
        Enables tool to set the map center to current lon/lat position.

        @param on_goto_current_position: The callback function to be called when
        user wants to center the map to current position.
        """
        goto_current_pos_btn = ToggleToolButton('goto-current-pos')
        goto_current_pos_btn.set_tooltip(_('Center map on my position.'))
        goto_current_pos_btn.connect('clicked', on_center_on_current_position)
        goto_current_pos_btn.set_active(GeoCanvas._CENTER_MAP)
        goto_current_pos_btn.show()
        self.insert(goto_current_pos_btn, -1)

    def enable_toggle_crosslines(self, view):
        """
        Enables tool to toggle crosslines.

        @param view: The view for which the crosslines shall be displayed.
        """
        toggle_crossline_btn = ToggleToolButton('toggle-crosslines')
        toggle_crossline_btn.set_tooltip(_('Show crossline.'))
        toggle_crossline_btn.set_active(GeoCanvas._CROSSLINES)
        toggle_crossline_btn.connect('clicked', view.toggle_crossline_cb)
        toggle_crossline_btn.show()
        self.insert(toggle_crossline_btn, -1)

    def enable_zoom(self, zoom_callbacks):
        """
        Enables tools to zoom the map via buttons.

        @param zoom_callbacks: A dict containing zoom callbacks:
                ===========  =============
                zoom_callbacks['zoom_in']   A callback to zoom in

                zoom_callbacks['zoom_out']  A callback to zoom out
                ===========  =============
        """
        self.zoom_in_btn = ToolButton('zoom-in')
        self.zoom_in_btn.set_tooltip(_('Zoom in.'))
        self.zoom_in_btn.connect('clicked', zoom_callbacks['zoom_in'])
        self.zoom_in_btn.show()
        self.insert(self.zoom_in_btn, -1)

        self.zoom_out_btn = ToolButton('zoom-out')
        self.zoom_out_btn.set_tooltip(_('Zoom out.'))
        self.zoom_out_btn.connect('clicked',  zoom_callbacks['zoom_out'])
        self.zoom_out_btn.show()
        self.insert(self.zoom_out_btn, -1)

        self.callbacks.update(zoom_callbacks)

    def enable_zoom_bestfit(self, on_zoom_bestfit):
        """
        Enables zoom-to-best-fit support on this toolbar.

        @param on_zoom_bestfit: The callback function to be called when user
        wants to zoom to best extent.
        """
        zoom_best_fit_btn = ToolButton('zoom-best-fit')
        zoom_best_fit_btn.set_tooltip(_('Zoom best fitting extent.'))
        zoom_best_fit_btn.connect('clicked', on_zoom_bestfit)
        zoom_best_fit_btn.show()
        self.insert(zoom_best_fit_btn, -1)

    def enable_navigation(self, nav_callbacks):
        """
        Enables tools to navigate the map via buttons.

        @param nav_callbacks: A dict containing navigation callbacks:
                ===========  =============
                nav_callbacks['west']   A callback to step west

                nav_callbacks['north']   A callback to step north

                nav_callbacks['south']   A callback to step south

                nav_callbacks['east']   A callback to step east
                ===========  =============
        """
        self._enable_step_west(nav_callbacks['west'])
        self._enable_step_north(nav_callbacks['north'])
        self._enable_step_south(nav_callbacks['south'])
        self._enable_step_east(nav_callbacks['east'])
        self.callbacks.update(nav_callbacks)

    def enable_custom_Button(self, button):
        """
        Inserts a custom button to the map toolbar.

        Consider to use it only, if it does not make much sense to place
        the button in its own toolbar (e.g. if there will be only one
        button, which might an extra toolbar dispensable).
        """
        self.insert(button, -1)

    def key_pressed_cb(self, widget, event, callbacks):
        """
        Callback handles all incoming keyevents and calls the appropriate
        callback-method.
        """
        keyname = gtk.gdk.keyval_name(event.keyval)
        #self._logger.debug('\'%s\' key pressed' % keyname)
        if(keyname in ['KP_Up']): # up
            self.set_focus_child(self.step_north_btn)
            callbacks['north'](None)
        elif(keyname in ['KP_Down']): # down
            self.set_focus_child(self.step_south_btn)
            callbacks['south'](None)
        elif(keyname in ['KP_Left']): #left
            self.set_focus_child(self.step_west_btn)
            callbacks['west'](None)
        elif(keyname in ['KP_Right']): #right
            self.set_focus_child(self.step_east_btn)
            callbacks['east'](None)
        elif(keyname in ['plus', 'KP_Add', 'KP_Page_Up']): # zoom in
            self.set_focus_child(self.zoom_in_btn)
            callbacks['zoom_in'](None)
        elif(keyname in ['minus', 'KP_Substract', 'KP_Page_Down']): # zoom out
            self.set_focus_child(self.zoom_out_btn)
            callbacks['zoom_out'](None)
        if self.view._CROSSLINES:
            self.view.motion_crosslines(self.view.fixed)

    def _enable_step_north(self, on_step_north):
        """
        Enables button to step north.

        @param on_step_north: The callback function to be called when the user
        wants to step north.
        """
        self.step_north_btn = ToolButton('step-north')
        self.step_north_btn.set_tooltip(_('Move North.'))
        self.step_north_btn.connect('clicked', on_step_north)
        self.step_north_btn.show()
        self.insert(self.step_north_btn, -1)

    def _enable_step_east(self, on_step_east):
        """
        Enables button to step east.

        @param on_step_east: The callback function to be called when the user
        wants to step east.
        """
        self.step_east_btn = ToolButton('step-east')
        self.step_east_btn.set_tooltip(_('Move East.'))
        self.step_east_btn.connect('clicked', on_step_east)
        self.step_east_btn.show()
        self.insert(self.step_east_btn, -1)

    def _enable_step_south(self, on_step_south):
        """
        Enables button to step south.

        @param on_step_south: The callback function to be called when the user
        wants to step south.
        """
        self.step_south_btn = ToolButton('step-south')
        self.step_south_btn.set_tooltip(_('Move South.'))
        self.step_south_btn.connect('clicked', on_step_south)
        self.step_south_btn.show()
        self.insert(self.step_south_btn, -1)

    def _enable_step_west(self, on_step_west):
        """
        Enables button to step west.

        @param on_step_west: The callback function to be called when the user
        wants to step west.
        """
        self.step_west_btn = ToolButton('step-west')
        self.step_west_btn.set_tooltip(_('Move West.'))
        self.step_west_btn.connect('clicked', on_step_west)
        self.step_west_btn.show()
        self.insert(self.step_west_btn, -1)

###############################################################################

class BoundingBox():
    """
    Represents the spatial extent of a feature as a rectangle.

    Axis ordering is lon/lat (although coordinates refer to EPSG:4326 CRS).
    """

    def __init__(self, lon_min, lat_min, lon_max, lat_max):
        """
        Creates boundingbox with corner coordinates.

        @note: All values expected to be in EPSG:4326.
        @param lon_min: The longitude of lower left.
        @param lat_min: The latitude of lower left.
        @param lon_max: The longitude of upper right.
        @param lat_max: The latitude of upper right.
        """
        self._logger = logging.getLogger('geo.BoundingBox')
        if lon_min is None or lon_max is None or \
                              lat_min is None or lat_max is None:
            self.lower_left = None
            self.upper_right = None
        else:
            self.lower_left = Point(lon_min, lat_min)
            self.upper_right = Point(lon_max, lat_max)
        #self._logger.debug('NEW BoundingBox: %s' % self.__str__())

    def is_empty(self):
        """
        Indicates if boundingbox was initialized with values or not.
        """
        return not (self.lower_left or self.upper_right)

    def reset(self):
        """
        Resets the BoundingBox.
        """
        self.lower_left = None
        self.upper_right = None

    def get_center(self):
        """
        Returns center (lon/lat) of boundingbox instance.
        """
        if not self.is_empty():
            return self.get_hrange() / 2.0, self.get_vrange() / 2.0

    def get_west(self):
        """
        Returns the west edge longitude of instance.
        """
        if not self.is_empty():
            return self.lower_left.x

    def get_east(self):
        """
        Returns the east edge longitude of instance.
        """
        if not self.is_empty():
            return self.upper_right.x

    def get_north(self):
        """
        Returns the north edge latitude of instance.
        """
        if not self.is_empty():
            return self.upper_right.y

    def get_south(self):
        """
        Returns the south edge latitude of instance.
        """
        if not self.is_empty():
            return self.lower_left.y

    def contains(self, position):
        """
        Returns True, if given position is contained by this instance,
        False otherwise.
        """
        if not self.is_empty() and \
            position.x > self.lower_left.x and \
            position.y > self.lower_left.y and \
            position.x < self.upper_right.x and \
            position.y < self.upper_right.y:
            #self._logger.debug('position %s is contained by %s', position, self)
            return True
        else:
            #self._logger.debug('position %s is not contained by %s', position, self)
            return False

    def merge(self, bbox):
        """
        Extends the boundingbox instance with the given bbox parameter.

        @param bbox: The boundingbox, this instance shall also contain.
        """
        if bbox is None or bbox.is_empty():
            return
        if self.is_empty():
            self.lower_left = bbox.lower_left
            self.upper_right = bbox.upper_right
            return

        #self._logger.debug('Merge bboxes %s and %s' % (self, bbox))
        if (self.lower_left.x + 200) > (bbox.lower_left.x + 200):
            self.lower_left.coords = (bbox.lower_left.x, self.lower_left.y)
        if (self.lower_left.y + 200) > (bbox.lower_left.y + 200):
            self.lower_left.coords = (self.lower_left.x, bbox.lower_left.y)
        if (self.upper_right.x + 200) < (bbox.upper_right.x + 200):
            self.upper_right.coords = (bbox.upper_right.x, self.upper_right.y)
        if (self.upper_right.y + 200) < (bbox.upper_right.y + 200):
            self.upper_right.coords = (self.upper_right.x, bbox.upper_right.y)
        #self._logger.debug('Merged bbox: %s' % self)

    def get_hrange(self):
        """
        Returns the width of this instance.
        """
        return self.upper_right.x - self.lower_left.x

    def get_vrange(self):
        """
        Returns the height of this instance.
        """
        return self.upper_right.y - self.lower_left.y

    def get_ratio(self):
        """
        Returns the ratio (height/width) of this instance.
        """
        return self.get_vrange() / self.get_hrange()

    def as_polygon(self):
        """
        Returns the instance as polygon (points clockwise).
        """
        return Polygon(((self.lower_left.x, self.lower_left.y),
                        (self.lower_left.x, self.upper_right.y), \
                        (self.upper_right.x, self.upper_right.y), \
                        (self.upper_right.x, self.lower_left.y)))

    def __str__(self):
        """
        Returns string representation of the instances values with
        lower_left corner and upper_right corner in lon/lat ordering.

        @return: 'bbox: [ll.x, ll.y, ur.x, ur.y]'
        """
        if self.is_empty():
            return 'bbox: empty'
        return 'bbox: %1.3f, %1.3f, %1.3f, %1.3f' % \
                            (self.lower_left.x, self.lower_left.y, \
                             self.upper_right.x, self.upper_right.y)

    @property
    def wkt(self):
        """
        Returns the well known text representation as polygon.
        """
        return self.as_polygon().wkt
