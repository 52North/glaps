"""@brief Main classes and functions for the geocache plugin."""
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
# Created: Oct 24, 2009
# Modified: $Date$
#       by: $Author: $
#
#endif
from sugar.activity.activity import Activity
import geomodel
__version__ = '$Id: geocacheplugin.py 182 2010-09-27 08:49:15Z  $'
import os
import gtk
import gobject
import logging

from sugar import profile
from groupthink.groupthink_base import UnorderedHandler
from sugar.graphics.toolbutton import ToolButton
from sugar.graphics.toggletoolbutton import ToggleToolButton


#import gettext
#gettext.bindtextdomain('myapplication', './po')
#gettext.textdomain('myapplication')
#_ = gettext.gettext
#
#print _('This is a translatable string.')

import utils
import constants

from utils import _
from utils import addto_icon_path
from osmtileview import OSMTileView
from geomodel import Player
from geomodel import GeoModel
from plugin import ActionProvider

import geojson
from shapely.geometry import Point
from shapely.geometry import shape
from groupthink import groupthink_base

# constants
INIT_SHOW_CACHE = False

# toogle booleans
_SHOW_CACHE = INIT_SHOW_CACHE
_CACHE_PLACED = False


###############################################################################

class GeoCache(ActionProvider, object):
    """
    TODO classdocs geocache
    """
    __gsignals__ = {'position_changed': (gobject.SIGNAL_RUN_LAST,
                                        gobject.TYPE_NONE,
                                        (gobject. TYPE_PYOBJECT,))
        }

    TITLE = _('GeoCache')
    DESCRIPTION = _('Find treasures hidden at a secret place.')
    ICONS_PATH = os.path.join(constants.BUNDLE_PATH, 'geocacheplugin/icons')

    center_on_first_position_handler = None

    def __init__(self, activity):
        """Constructor.

        TODO Add description here
        """
        ActionProvider.__init__(self, self.TITLE, self.DESCRIPTION,
                                os.path.join(self.ICONS_PATH, 'geocache.svg'))
        addto_icon_path(self.ICONS_PATH)

        self._logger = logging.getLogger('GeoCache')
        self._logger.setLevel(constants.LOG_LEVEL)

        self.map = OSMTileView(activity)
        self.model = GeoCacheModel(activity, self.map)

        self.map.register_toolbars(activity.toolbox)
        activity.toolbox.set_current_toolbar(1)
        activity.toolbox.add_toolbar(_('Geocaching tools'),
                                     GeoCacheToolbar(self.map, activity, self.model))

        canvas = gtk.HBox()
        canvas.pack_start(self.map)

        activity.set_view(canvas)
        canvas.show_all()

        # create shared datastructure for treasure
        self.treasure = groupthink_base.Recentest(None)
        self.treasure.HANDLER_TYPE = UnorderedHandler
        activity.cloud.treasure = self.treasure
        self.center_on_first_position_handler = activity.connect("position_changed",
                                                                 self.map.init_center)


###############################################################################

class GeoCacheModel(GeoModel):

    def __init__(self, activity, view):
        """
        Creates geocache model.
        """
        GeoModel.__init__(self, activity)
        self._logger = logging.getLogger('geocacheplugin.GeoCacheModel')
        self._logger.setLevel(constants.LOG_LEVEL)

        # register collaboration handlers
        self._register_collaboration_callbacks(activity,
                                               self.__player_joined_cb,
                                               self.__player_left_cb)

        # Because groupthink ignores "deep changes" in a shared object, we
        # have to ensure, these will be re-set with an own callback mechanism.
        player = self.players[self.mynickname]
        player.connect('player_changed', self.__player_changed_cb)

        self._logger.debug("INIT GEOCACHEMODEL DONE.")

    def __player_changed_cb(self, player):
        """
        Implemented callback method for updating the own player.

        Actually, this method only re-sets the player in the collaborative
        datastructure to let the changes be exposed by groupthink.

        @param player: The player, which has been changed/updated.
        @see: L{GeoModel}
        """
        self._logger.debug('__player_changed_cb(): %s', player)
        self.players[self.mynickname] = player
        self._logger.debug('player updated: %s', player)

    #################### IMPLEMENTED METHODS #################################

    def __player_joined_cb(self, activity, buddy):
        self._logger.debug('_player_joined_cb()')

    def __player_left_cb(self, activity, buddy):
        self._logger.debug('__player_left_cb()')
        name = buddy.get_property('nick')
        self._logger.debug("player '%s' is leaving", name)
        try:
            self._logger.debug(self.view.drawn_players)
            if name in self.view.drawn_players:
                self.view.drawn_players.remove(name)
            del self.players[name]
        except:
            # already deleted
            pass

###############################################################################

class GeoCacheToolbar(gtk.Toolbar):
    """
    Contains tools for geocaching.
    """

    show_cache = None

    def __init__(self, view, activity, model):
        gtk.Toolbar.__init__(self)
        self._logger = logging.getLogger('GeocachingToolbar')
        self._logger.setLevel(constants.LOG_LEVEL)

        self.view = view
        self.model = model
        self.activity = activity

#        #########################################################
#        # XXX create a geocache (hardcoded for usability testing)
#        # XXX put XO name with coordinate into "caches" file
#        self.cache = Point()
#        file_ = None
#        try:
#            file_ = open(os.path.join(constants.BUNDLE_PATH, 'caches'))
#            from sugar import profile
#            nick = profile.get_nick_name()
#            lines = file_.readlines()
#            for line in lines:
#                entries = line.split(',')
#                if nick == entries[0]:
#                    lon = float(entries[1])
#                    lat = float(entries[2])
#                    self.cache.coords = (lon,lat)
#        finally:
#            if file_ is not None:
#                file_.close()
#        self._logger.debug('cache: %s', self.cache.wkt)
#        #########################################################

        # individualize cache symbol and enable cache button
        img_name = os.path.join(GeoCache.ICONS_PATH, 'show-cache.svg')
        color_stroke = profile.get_color().get_stroke_color()
        color_fill = profile.get_color().get_fill_color()
        self._cache_overlay = utils.load_svg_image(img_name,
                                                   color_stroke,
                                                   color_fill,
                                                   size=(40,40))

        if not activity.get_shared() or (activity.get_shared() and activity.initiating):
            # only initiating activity creates "place-cache" button
            place_cache = ToolButton('place-cache')
            place_cache.set_tooltip(_('Place treasure.'))
            place_cache.connect('clicked', self._on_place_cache)
            place_cache.show()
            self.insert(place_cache, -1)

        self.show_cache = ToggleToolButton('show-cache')
        self.show_cache.set_tooltip(_('Show treasure.'))
        self.show_cache.set_active(INIT_SHOW_CACHE)
        self.show_cache.connect('clicked', self._on_show_cache)
        self.show_cache.show()
        self.insert(self.show_cache, -1)

        self.export_csv = ToolButton('csv-export')
        self.export_csv.set_tooltip(_('Export to CSV.'))
        self.export_csv.connect('clicked', self.model.export_to_csv)
        self.export_csv.show()
        self.insert(self.export_csv, -1)

        self.show()

    def _on_show_cache(self, button):
        if button.get_active():
            factory = lambda ob: geojson.GeoJSON.to_instance(ob)
            cache = self.activity.cloud.treasure.get_value()
            if cache is not None:
                position_dump = geojson.loads(cache, object_hook=factory)
                position = shape(position_dump)
                self._logger.debug("type of position: %s", type(position))
                self.view.drawable.draw_overlay(self._cache_overlay, position)
        else:
            self.view.drawable.remove_overlay(self._cache_overlay)

    def _on_place_cache(self, button):
        pos = geojson.dumps(self.activity.gps_position)
        if pos is not None:
            self.activity.cloud.treasure.set_value(pos)
            self._CACHE_PLACED = True
            self._logger.debug('cache placed')
            self.show_cache.set_active(True)
            self._on_show_cache(self.show_cache)
