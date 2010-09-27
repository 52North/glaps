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
__version__ = '$Id: geomodel.py 175 2010-09-25 11:46:37Z  $'

import os
import gtk
import dbus
import time
import logging
import gobject

from sugar import profile
from sugar.presence import presenceservice
from sugar.graphics.alert import NotifyAlert

import utils
import constants
import geojson

from utils import _

from groupthink.groupthink_base import CausalDict
from groupthink.groupthink_base import string_translator
from shapely.geometry import Point
from shapely.geometry import shape

_LOG = logging.getLogger('geomodel')
_LOG.setLevel(logging.DEBUG)

###############################################################################

def player_translator(val, pack):
    """
    Translator function to pack or unpack player items before network
    communication via groupthink.

    A L{CausalDict} entry represents the player itself, so this function
    wraps the players attributes appropriately as strings. For convenience
    the geojsons L{geojson.Feature} is used. The players attributes--except
    geometry and feature_collection--are stored within the extra 'magic'.
    """
    #_LOG.debug("""player_translator():
    #            val=%s""", val)
    player_id = constants.PLAYER_ID
    if pack:
        #_LOG.debug("features: %s", val.feature_collection)
        feature = geojson.Feature(id=player_id, geometry=val.position,
                                  properties=val.features,
                                  nickname=val.nickname,
                                  color_fill=val.color_fill,
                                  color_stroke=val.color_stroke,
                                  old_position=val.oldpos)
        #_LOG.debug('output: %s', feature)
        return geojson.dumps(feature)
    else:
        factory = lambda ob: geojson.GeoJSON.to_instance(ob)
        feature = geojson.loads(val, object_hook=factory)
        if feature.id != player_id:
            raise ValueError, 'Value to unpack is not a Player object.'
        else:
            #_LOG.debug("feature: %s", feature)
            #_LOG.debug("feature.props: %s", feature.properties)
            nickname = feature.extra['nickname']
            player = Player(nickname, feature.properties)
            player.position = shape(feature.geometry)
            # override individual colors
            player.color_stroke = feature.extra['color_stroke']
            player.color_fill = feature.extra['color_fill']
            if feature.extra['old_position']:
                player.oldpos = shape(feature.extra['old_position'])
            else:
                player.oldpos = None
            return player

###############################################################################

class Player(gobject.GObject):
    """
    The Player class is the central representation of the xo user.

    The player contains (among other, more player-centric attributes)
    a position and several L{Feature}s which might represent other
    geoobjects. A Feature object is a L{geojson.feature.Feature}, which
    can be extended arbitrarily via its properties Map. However, the
    mandatory attribute id shall represent an application unique type, like
    L{constants.PLAYER_FEATURE_ID}, but could also be specified more
    finegrained than the example.
    """

    __gsignals__ = {
            'position_changed': (gobject.SIGNAL_RUN_LAST,
                                 gobject.TYPE_NONE,
                                 (gobject. TYPE_PYOBJECT,)),
            'player_changed': (gobject.SIGNAL_RUN_LAST,
                               gobject.TYPE_NONE,
                               ())
         }

    ICON_SIZE = (30,30)

    trace = dict() # { 'time.time()': position }
    oldpos = None # used, to not emit unnecessary changes.
    icon = None

    def __init__(self, nickname, properties=None):
        """
        Initializes a player.

        @param nickname: The players name.
        @param properties: A list containing features.
        """
        gobject.GObject.__init__(self)
        self._logger = logging.getLogger('player.' + nickname)
        self._logger.setLevel(constants.LOG_LEVEL)

        # players properties
        self.nickname = nickname
        self.position = Point(0,0)
        self.trace = dict()

        # set colors of the current player as default
        self.color_fill = profile.get_color().get_fill_color()
        self.color_stroke = profile.get_color().get_stroke_color()

        # the players features
        if properties is None:
            self.feature_collection = geojson.FeatureCollection(features=list())
        else:
            self.feature_collection = geojson.FeatureCollection(features=properties)

    def __str__(self):
        player = "Player: " + self.nickname + ', ' + str(self.position) + '['
        for feature in self.features:
            player += str(feature)
        player += ']'
        return player

    def _get_features(self):
        return self.feature_collection.features
    features = property(_get_features)

    def has_feature(self, feature):
        """
        Checks, if the given feature is hosted by this player.

        @param feature: the feature to check.
        """
        return feature in self.features

    def add_feature(self, feature):
        """
        Convenience method for adding new features to the player. Emits
        also a player changed signal.

        @param feature: The feature to add.
        @note: Emits a 'player_changed' signal to indicate the change.
        """
        self.features.append(feature)
        self.emit('player_changed')
        self._logger.debug("emit player_changed")

    def remove_feature(self, feature):
        """
        Removes a feature from the player.

        @param feature: The feature to remove.
        @note: Emits a 'player_changed' signal to indicate the change.
        """
        self.features.remove(feature)
        self.emit('player_changed')
        self._logger.debug("emit player_changed")

    def set_color(self, fill=profile.get_color().get_fill_color(), \
                  stroke=profile.get_color().get_stroke_color()):
        """
        Sets the xo colors for this player.

        @param fill: hex string for fill color.
        @param stroke: hex string for stroke color.
        """
        self.color_stroke = stroke
        self.color_fill   = fill

    def set_position(self, source, new_pos):
        """
        Callback method to set a new position for the player.

        @param source: the source emitted the signal
        @param new_pos: the new position as L{shapely.geometry.Point}.
        @note: Emits a 'player_changed' signal to indicate the change.
        """
#        self._logger.debug("set new position: %s", new_pos)
        self.oldpos = self.position
        self.position = new_pos

        # only emit changes when moved
        if self.has_moved():
            time_stamp = str(time.time())
            self.trace[time_stamp] = self.position
            self._logger.debug("emit player_changed")
            self.emit('player_changed')

    def get_position(self):
        """
        Returns the current location as L{shapely.geometry.Point}.

        @return: the current position or Point(0,0), if no GPS
                 is currently available.
        """
        if self.position:
            return self.position
        else:
            self._logger.info('No GPS signal available.')
            return Point()

    def has_moved(self):

        """
        Indicates if player has moved.

        @note: We want to avoid 'jumping' of the player, when the player
        does not move (this occures naturally, due to inexactness of GPS).
        This method indicates movement only, if the player has moved out
        of a specified buffer around the current position once set. Once, the
        player has moved out the buffer, the current position will be set and
        the player has moved.

        @return: True, if player has moved noticably, False if not.
        """
        if not self.oldpos:
            return True
        delta_x = abs(self.oldpos.x - self.position.x)
        delta_y = abs(self.oldpos.y - self.position.y)
        return delta_x > constants.SPACE_DISCRETION or \
               delta_y > constants.SPACE_DISCRETION


    def get_icon(self):
        """
        Returns the individualized XO icon for this player.
        """
        if self.icon is None:
            self._logger.debug("create new icon for player '%s'", self.nickname)
            self.icon = utils.get_xo_icon(self.color_stroke,
                                          self.color_fill,
                                          size=self.ICON_SIZE)
        return self.icon

###############################################################################

# register signal emitter
gobject.type_register(Player)

###############################################################################

class GeoModel():
    """
    The GeoModel holds common data like the collaborative datastructure
    where all joined players are stored. It offers an export callback
    to export all players into a CSV file.
    """

    __gsignals__ = {
            'position_changed': (gobject.SIGNAL_RUN_LAST,
                                 gobject.TYPE_NONE,
                                 (gobject. TYPE_PYOBJECT,)),
            'player_changed': (gobject.SIGNAL_RUN_LAST,
                               gobject.TYPE_NONE,
                               ())
         }

    def __init__(self, activity):

        self._logger = logging.getLogger('GeoModel')
        self._logger.setLevel(constants.LOG_LEVEL)
        self.activity = activity
        self.activity.set_model(self)

        # Init the player list
        self.mynickname = profile.get_nick_name()
        self.pservice = presenceservice.get_instance()
        self.owner = self.pservice.get_owner()

        # create shared datastructure for players
        self.players = CausalDict(value_translator=player_translator)
        activity.cloud.players = self.players
        this_player = Player(self.mynickname)
        self.players[self.mynickname] = this_player
        #gobject.timeout_add(3000, self.print_dict) # only for debugging

        activity.connect('position_changed', this_player.set_position)

        self._logger.debug("INIT GEOSPACEMODEL DONE.")

    def _register_collaboration_callbacks(self, activity, player_joined_cb, player_left_cb):
        """
        Registers collaboration callbacks, when model shall listens
        and handles sharing/joining signals. This late registration
        is important for models (subclassing this class) which
        have to create a their structure first, before first sharing
        or joining signals were emitted.

        @param activity: the activity, to which signals we want to connect to.
        @param player_joined_cb: The callback, handling a player_joined event.
        @param player_left_cb: The callback, handling a player_left event.
        """
        # register change listener
        activity.connect('shared', self._register_cb, player_joined_cb, player_left_cb)
        shared = activity._shared_activity
        if shared:
            shared.connect('buddy-joined', player_joined_cb)
            shared.connect('buddy-left', player_left_cb)

    def _register_cb(self, activity, player_joined_cb, player_left_cb):
        """
        We can connect to 'buddy-joined' and 'buddy-left', after activity
        was shared by the user. This does not have any effect on joined
        activities, since these never receive the 'shared' signal.

        @param activity: the activity where to get the shared instance from.
        @param player_joined_cb: The callback, handling a player_joined event.
        @param player_left_cb: The callback, handling a player_left event.
        """
        self._logger.debug('Activity shared.')
        shared = activity._shared_activity
        shared.connect('buddy-joined', player_joined_cb)
        shared.connect('buddy-left', player_left_cb)

    def print_dict(self):
        """
        For debugging: log out the shared datastructure pretty printed.
        """
        self._logger.debug("print_dict()")
        for name in self.players.keys():
            self._logger.debug("key: %s => value: %s", name, self.players[name])
        return True # loop timeout callback

    ##########################################################################

    def __update_players_cb(self, added, removed):
        """
        Callback triggered by L{groupthink} when model has changed.

        @param added: a dictionary containing names mapping to players to be added.
        @param removed: a dictionary containing names mapping to players to be removed.

        @note: Implement if necessary.
        """
        raise NotImplementedError

    def __player_changed_cb(self, player):
        """
        Callback method when the own player has changed.

        @param player: The player, which has been changed/updated.
        """
        raise NotImplementedError

    def export_to_csv(self, button):
        """
        Export all participating players into a csv file.
        """
        import csv
        from datetime import datetime
        csv_path = os.path.join(os.path.abspath('../../../'), '%s_geo-export.csv' %
                                (datetime.now().isoformat()))
        csv_path = csv_path.replace(':', '_')
        _LOG.debug('cvs_path: %s' % csv_path)

        csv_file = open(csv_path, "w")
        csv_writer = csv.writer(csv_file)
        header = ['Nickname', 'Trace', 'Fillcolor', 'Strokecolor', 'FeatureCollection']
        csv_writer.writerow(header)
        for key in self.players.keys():
            player = self.players[key]
            nick = player.nickname

            trace = list()
            for key in player.trace.keys():
                trace.append((key, player.trace[key]))
            trace = str(trace.sort())

            fill = player.color_fill
            stroke = player.color_stroke
            features = str(player.features)

            csv_writer.writerow((nick, trace, fill, stroke, features))
        csv_file.flush()
        csv_file.close()

        alert = NotifyAlert()
        alert.props.title = _('Export')
        alert.props.msg = _('CSV export written to %s.' % csv_path)
        self.activity.add_alert(alert)
        alert.connect('response', self.dismiss_alert_cb)

    def dismiss_alert_cb(self, alert, response_id):
        self.activity.remove_alert(alert)

    def __export_game_to_kmz(self):
        """
        Exports all players to kmz. This method is available for the player
        initiated the game and exports all players' status.
        """
        raise NotImplementedError

    def export_to_kml(self, player):
        """
        Exports player to kml format

        @note: Imlement if necessary.
        """
        raise NotImplementedError