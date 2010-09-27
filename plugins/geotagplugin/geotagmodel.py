"""
Defines what data is used by the geotagplugin and how the data used
will be displayed.
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
# Created: Jan 5, 2010
# Modified: $Date$
#       by: $Author: $
#
#endif
__version__ = '$Id: geotagmodel.py 182 2010-09-27 08:49:15Z  $'
import os
import sys
import gtk
import gobject
import logging
import zipfile
import datetime
import traceback

from sugar import profile
from sugar.graphics.alert import NotifyAlert

import utils
import constants
import geojson

from utils import _
from utils import get_buddy_from_handle
from geomodel import GeoModel
from geomodel import Player

from shapely.geometry import Point
from shapely.geometry import shape

###############################################################################

class GeoTagModel(gtk.ScrolledWindow, GeoModel):
    """
    Model containing common data used during the play. This includes the
    players and their position, traces and data, like observed features.
    Also, the model does the sync job via collaboration tubes via groupthink.

    It inherits L{gtk.ScrolledWindow} and provides the player within a
    L{gtk.Treeview} to be embeddable into the actual play canvas.
    """

    selected_feature = None
    row_references = dict()     # category name => row_reference
    feature_references = dict() # { player.nick: list() } list: '<category>_time.time())'
    category_overlays = dict()   # { '<category>_time.time())': overlay }
    features_to_draw = dict()     # { '<category>': list() } list: pixbuf/overlay
    FEATURE_IMG_SIZE = (30, 30)

    _columns = 6
    (COL_TOGGLE, COL_TOGGLE_VISIBLE, COL_ICON, COL_TEXT, COL_OBJECT, COL_PLAYER_NAME) = range(_columns)

    def __init__(self, activity, view):
        """
        Creates geotag model containing current state of the buddies joined
        this activity.
        """
        gtk.ScrolledWindow.__init__(self)
        GeoModel.__init__(self, activity)
        self._logger = logging.getLogger('geotagplugin.GeoTagModel')
        self._logger.setLevel(constants.LOG_LEVEL)
        self.set_size_request(280, 815)
        self.view = view

        self._logger.debug("init GEOTAG_MODEL ...")

        # create treeview
        self._model = gtk.TreeStore(gobject.TYPE_BOOLEAN, # checkbox
                                    gobject.TYPE_BOOLEAN, # checkbox visible?
                                    gtk.gdk.Pixbuf, # icon
                                    gobject.TYPE_STRING, # name
                                    gobject.TYPE_PYOBJECT, # instance/value
                                    gobject.TYPE_STRING)   # player_name

        self.treeview = gtk.TreeView(self._model)
        self.treeview.set_property('can-focus', False)
        self.treeview.get_selection().connect("changed", self.selection_cb)

        # create cell renderers
        renderer_toggle = gtk.CellRendererToggle()
        renderer_pixbuf = gtk.CellRendererPixbuf()
        renderer_text = gtk.CellRendererText()
        renderer_toggle.connect("toggled", self.toggled_category_cb)

        treecolumn_text = gtk.TreeViewColumn(_("Categories"), renderer_text, text=self.COL_TEXT)
        treecolumn_pixbuf = gtk.TreeViewColumn('', renderer_pixbuf, pixbuf=self.COL_ICON)
        treecolumn_toggle = gtk.TreeViewColumn(_('View'), renderer_toggle, active=self.COL_TOGGLE)

        treecolumn_pixbuf.set_property("resizable", False)
        treecolumn_toggle.set_property("resizable", False)
        treecolumn_text.set_property("resizable", False)

        treecolumn_toggle.add_attribute(renderer_toggle, "active", self.COL_TOGGLE)
        treecolumn_toggle.add_attribute(renderer_toggle, "visible", self.COL_TOGGLE_VISIBLE)

        self.treeview.append_column(treecolumn_toggle)
        self.treeview.append_column(treecolumn_pixbuf)
        self.treeview.append_column(treecolumn_text)

        # add all available categories
        import geotagplugin # avoid circular imports
        self.categories = geotagplugin.get_categories()
        for category in self.categories:

            # TODO add to tree, only when first cat is available
            # TODO add count in paranthesis?

            self.features_to_draw[category] = list()

            icon_path = os.path.join(geotagplugin.GeoTag.ICONS_PATH, category + '.svg')
            icon = utils.load_svg_image(icon_path, None, None)
            toggle = gtk.ToggleButton()

            # add entries and hold a reference
            entries = self.get_entries(icon, toggle, category, None, None)
            iter = self._model.prepend(None, entries)
            path = self._model.get_path(iter)
            self.row_references[category] = gtk.TreeRowReference(self._model, path)

        # Because groupthink ignores "deep changes" in a shared object, we
        # have to ensure, these will be re-set with an own callback mechanism.
        player = self.players[self.mynickname]
        player.connect('player_changed', self.__player_changed_cb)

        self.treeview.expand_all()
        self.add_with_viewport(self.treeview)
        self.show_all()

        # register collaboration handlers
        self._register_collaboration_callbacks(activity,
                                               self.__player_joined_cb,
                                               self.__player_left_cb)


        # we have to keep model in sync with the own player, but also
        # with all other players contributing the game. This has to be done
        # via the shared datastructure hold by geomodel.GeoModel.
        self.players.register_listener(self.__update_players_cb)


        # if players are already present, add their tagged features
        if len(self.players) > 0:
            for name in self.players.keys():
                player = self.players[name]
                self._update_players_features(player)

        self._logger.debug("... init GEOTAG_MODEL DONE.")


    def get_entries(self, icon=None, toggle=None, text=None, player_name=None, object=None):
        """
        Sets the given entries step-by-step. Defines one place, to order
        all tree entries the same way.

        @param icon: the pixbuf to set.
        @param toggle: the gtk.ToggleButton to set.
        @param text: the text to be displayed.
        @param player_name: the player's name to reference a tagged category.
        @param object: the actual object, the entry represents
        """
        # (COL_ICON, COL_TOGGLE, COL_NAME, COL_OBJECT, COL_PLAYER_NAME)
        entries = [None] * self._columns

        entries[self.COL_ICON] = icon
        entries[self.COL_TOGGLE] = toggle
        if toggle is not None:
            show_toggle = True
        else:
            show_toggle = False
        entries[self.COL_TOGGLE_VISIBLE] = show_toggle
        entries[self.COL_TEXT] = text
        entries[self.COL_PLAYER_NAME] = player_name
        entries[self.COL_OBJECT] = object
        self._logger.debug("entries: %s", entries)
        return entries

    def toggled_category_cb(self, renderer, path):
        """
        Callback, when user has changed selection of category view toggle button.
        Active toggle button will draw all features from this category on the
        map, inactive toggle button will remove all drawn features from map.

        @param renderer: The toggle button renderer from treeview.
        @param path: Path to the toggle button within the treeview.
        """
        self._logger.debug("toggled_category_cb()")
        # change toggle state
        is_active = not renderer.get_active()
        iter = self._model.get_iter(path)
        self._model.set_value(iter, self.COL_TOGGLE, is_active)

        # draw/remove overlays on map
        from geotagplugin import GeoTag # avoid circular imports
        if self._model.iter_has_child(iter):
            category = self._model.get_value(iter, self.COL_TEXT)
            if is_active:
                # draw the features
                self._logger.debug("draw features of category '%s'", category)
                overlays_and_positions = list()
                iter = self._model.iter_children(iter)
                while iter:
                    feature = self._model.get_value(iter, self.COL_OBJECT)
                    player_name = self._model.get_value(iter, self.COL_PLAYER_NAME)
                    player = self.players[player_name]
                    (fill, stroke) = (player.color_fill, player.color_stroke)
                    icon_name = feature.properties['icon_name']
                    icon_path = os.path.join(GeoTag.ICONS_PATH, icon_name + '.svg')
                    overlay = utils.load_svg_image(icon_path, stroke, fill, self.FEATURE_IMG_SIZE)

                    self.features_to_draw[category].append(overlay)
                    self.view.drawable.draw_overlay(overlay, shape(feature.geometry))
                    iter = self._model.iter_next(iter)
            else:
                # remove the features
                self._logger.debug("remove features of category '%s'", category)
                overlays_to_remove = self.features_to_draw[category]
                for overlay in overlays_to_remove:
                    self.view.drawable.remove_overlay(overlay)

    def add_feature(self, feature, geometry, category):
        """
        Adds new feature to the model. Delegates drawing to the view's/map's
        drawing component.

        @param feature: The feature to add/draw.
        @param geometry: Where the overlay shall be drawn.
        @param category: The category the overlay belongs to.
        """
        self.view.drawable.draw_overlay(feature, geometry)
        self.features_to_draw[category].append(feature)

    def remove_feature(self, overlay, category):
        """
        Removes a feature, so it is not drawn on the map.

        @param overlay: the feature overlay to remove.
        @param category: the category, the feature belongs to.
        """
        self._logger.debug("remove_feature()")
        if overlay in self.features_to_draw[category]:
            self._logger.debug("removing feature to draw %s", overlay)
            self.features_to_draw[category].remove(overlay)
            self.view.drawable.remove_overlay(overlay)

    def _update_players_features(self, player):
        """
        Updates the features of the given player within the treemodel.

        @param player: The updated players.
        """
        self._logger.debug("_update_players_features()")
        from geotagplugin import GeoTag # avoid circular imports

        (fill, stroke) = (player.color_fill, player.color_stroke)
        players_features = self.feature_references[player.nickname]

#        self._logger.debug("players.features (before): %s", player.features)
#        self._logger.debug("players_features (before): %s", players_features)

        # check, if features were added
        for feature in player.features:
            id = feature.id
            cat_name = id[id.rfind('.') + 1:] # cut prefix
            path = self.row_references[cat_name].get_path()
            cat_iter = self._model.get_iter(path) # on category

            ref_string = cat_name + "_" + feature.properties['time_stamp']
            if ref_string not in players_features:
                # add new tagged feature
                icon_name = feature.properties['icon_name']
                icon_path = os.path.join(GeoTag.ICONS_PATH, icon_name + '.svg')
                overlay = utils.load_svg_image(icon_path, stroke, fill, self.FEATURE_IMG_SIZE)
                self.add_feature(overlay, shape(feature.geometry), cat_name)
                #self.features_to_draw[cat_name].append(overlay)

                description_text = None
                if feature.properties['description'] is None:
                    description_text = cat_name
                else:
                    description_text = feature.properties['description']

                # add feature to tree
                entries = self.get_entries(overlay, None, description_text, player.nickname, feature)
                self._model.prepend(cat_iter, entries)
                players_features.append(ref_string)
                self._logger.debug("added %s to tree", ref_string)

        # check, if features were deleted
        for ref_string in players_features:
            self._logger.debug("ref_string of feature: %s", ref_string)
            cat_name = ref_string[: ref_string.rfind('_')] # get category
            feature_ts = ref_string[ref_string.rfind('_') + 1 :] # get timestamp
            self._logger.debug("feature_ts: %s", feature_ts)

            path = self.row_references[cat_name].get_path()
            cat_iter = self._model.get_iter(path) # on category
            cat_iter = self._model.iter_children(cat_iter) # on first

            # check if still present in player
            found = False
            for feature in player.features:
                if feature.properties['time_stamp'] == feature_ts:
                    found = True
                    break;

            if not found:
                while cat_iter:
                    player_name = self._model.get_value(cat_iter, self.COL_PLAYER_NAME)
                    if player_name == player.nickname:
                        feature_in_tree = self._model.get_value(cat_iter, self.COL_OBJECT)
                        self._logger.debug("feature in tree: %s", feature_in_tree)
                        time_stamp = feature_in_tree.properties['time_stamp']
                        if feature_ts == time_stamp:
                            self._logger.debug("delete feature in tree")
                            parent = self._model.iter_parent(cat_iter)
                            self.treeview.get_selection().select_iter(parent)
                            # remove references
                            players_features.remove(ref_string)
                            # remove from tree
                            self._model.remove(cat_iter)
                            self.selected_feature = None
                            break; # exit while loop
                        else:
                            cat_iter = self._model.iter_next(cat_iter)
                    else:
                        cat_iter = self._model.iter_next(cat_iter)

#        self._logger.debug("players.features (after): %s", player.features)
#        self._logger.debug("players_features (after): %s", players_features)
#        self._logger.debug('updated features of player: %s', player.features)

    def selection_cb(self, treeselection):
        """
        Delegates to display the selected information on the map.
        """
        model, _iter = treeselection.get_selected()
        self.selected_feature = model.get_value(_iter, self.COL_OBJECT)
        self._logger.debug("selected in tree: %s" % self.selected_feature)

    #################### IMPLEMENTED METHODS #################################

    def __update_players_cb(self, added, removed): # TODO REFACTOR ?
        """
        Callback method to fill model tree, when player constellation changes.

        @param added: a dictionary containing names mapping to players to be added.
        @param removed: a dictionary containing names mapping to players to be removed.
        @see: L{GeoModel}
        """
        self._logger.debug('__update_players_cb()')
        from geotagplugin import GeoTag # avoid circular imports

        # filter existing players, whose want to be updated
        update = dict()
        for key in removed:
            if key in added:
                update[key] = added[key]
        for key in update:
            del added[key]
            del removed[key]
        for key in update:
            player = update[key]
            self._logger.debug('Player "%s" updated', key)
            self._update_players_features(player)

        # remove tagged items from tree, when players has left the game
        for name in removed:
            player = self.players[name]

            # remove item, tagged by player
            for feature in player.features:
                # TODO (update count, if present)

                # get category in tree
                id = feature.id
                cat_name = id[id.rfind('.') + 1:] # cut prefix
                path = self.row_references[cat_name].get_path()
                cat_iter = self._model.get_iter(path) # on category
                while cat_iter:
                    cat_in_tree = self._model.get_value(cat_iter, self.COL_TEXT)
                    if cat_in_tree == cat_name:
                        self._model.remove(cat_iter)
                        break; # exit while loop
                    cat_iter = self._model.iter_next(cat_iter)

        # add tagged items to tree, when players join the game
        for name in added:
            player = self.players[name]
            feature_refs = list()
            self.feature_references[player.nickname] = feature_refs
            (fill, stroke) = (player.color_stroke, player.color_fill)

            self._logger.debug("players.features: %s", player.features)
            for feature in player.features:
                # add tagged items to its category
                # TODO (update count, if present)

                icon_name = feature.properties['icon_name']
                icon_path = os.path.join(GeoTag.ICONS_PATH, icon_name + '.svg')
                feature_icon = utils.load_svg_image(icon_path, stroke, fill, self.FEATURE_IMG_SIZE)

                # get category in tree
                id = feature.id
                cat_name = id[id.rfind('.') + 1:] # cut prefix
                path = self.row_references[cat_name].get_path()
                cat_iter = self._model.get_iter(path) # on category
                entries = self.get_entries(feature_icon, None, cat_name, name, feature)
                self._model.prepend(cat_iter, entries)

                # references to feature
                time_stamp = feature.properties['time_stamp']
                ref_string = cat_name + "_" + time_stamp
                feature_refs.append(ref_string)

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
        self._update_players_features(player)
        # redraw player on map
        if player.nickname in self.view.drawn_players:
            del self.view.drawn_players[player.nickname]
        #self.view._draw_player_on_map(player.nickname)
        self._logger.debug('player updated: %s', player)

    def __player_joined_cb(self, activity, buddy):
        self._logger.debug('_player_joined_cb()')

    def __player_left_cb(self, activity, buddy):
        self._logger.debug('__player_left_cb()')
        name = buddy.get_property('nick')
        try:
            # groupthink ignores own messages, so remove user manually
            self.__update_players_cb({}, {name : self.players[name]})
            if name in self.view.drawn_players:
                self.view.drawn_players.remove(name)
            del self.players[name]
        except:
            # already deleted
            pass


    ########################## EXPORT #########################################

    def _get_categories_as_styles(self, player):
        """
        """
        styles = ''
        export_tmp = os.path.join(constants.BUNDLE_PATH, 'geotagplugin/kmz_export')
        svg_path = os.path.join(constants.BUNDLE_PATH, 'geotagplugin/icons')
        png_path = os.path.join(export_tmp, 'icons')
        for feature in player.features:
            # write svg's to colored png's
            feature_name = feature.id[feature.id.rfind('.') + 1:]
            feature_svg = os.path.join(svg_path, feature_name + '.svg')
            icon_name = player.nickname + '_' + feature_name + '.png'
            output_png = os.path.join(png_path, icon_name)
            stroke = player.color_stroke
            fill = player.color_fill
            pixbuf = utils.load_svg_image(feature_svg, stroke, fill, (40,40))
            pixbuf.save(output_png, 'png')

            styles = styles + "<Style id='%s'>\n" % (player.nickname + '_' + feature_name)
            styles = styles + "<IconStyle>\n"
            styles = styles + "<Icon>\n"
            styles = styles + "<href>icons/%s</href>\n" % icon_name
            styles = styles + "</Icon>\n"
            styles = styles + "</IconStyle>\n"
            styles = styles + "</Style>\n"
        return styles

    def _get_feature_as_placemark(self, feature, icon_id):
        """
        Creates the xml part for a placemark for the given feature and its
        appropriate icon (colored from player's colors).
        """
        self._logger.debug("_get_feature_as_placemark()")
        try:
            point = shape(feature.geometry)
            category = feature.id[feature.id.rfind('.') + 1 :]
            placemark = '<Placemark id="%s">\n' % category
            placemark = placemark + '<name>%s</name>\n' % category
            placemark = placemark + '<description>\n'
            placemark = placemark + '%s\n' % feature.properties['description']
            placemark = placemark + '</description>\n'
            placemark = placemark + '<styleUrl>\n'
            placemark = placemark + '#%s\n' % icon_id # style id
            placemark = placemark + '</styleUrl>\n'
            placemark = placemark + '<Point>\n'
            placemark = placemark + '<coordinates>\n'
            placemark = placemark + '%s,%s\n' % (point.x, point.y)
            placemark = placemark + '</coordinates>\n'
            placemark = placemark + '</Point>\n'
            placemark = placemark + '</Placemark>\n'
            self._logger.debug("Placemark: %s", placemark)
        except:
            raise
        return placemark

    def export_to_kml(self, player):
        """
        Clears the export_tmp directory and a kml file containing the player's
        Document which describes the player's tagging results. Also copies the
        used icons for each tagged category as color-individualized pngs.

        @param player: The player to export.
        @return: the path where the player has been exported.
        """
        export_tmp = os.path.join(constants.BUNDLE_PATH, 'geotagplugin/kmz_export')

        # clear export directory
        def clear_files_from_dir(path):
            """
            Walks top-down recursively from given path and removes all files.
            """
            for the_file in os.listdir(path):
#                self._logger.debug("clear path %s", path)
                if not the_file.startswith('.'):
                    file_path = os.path.join(path, the_file)
                    try:
                        if os.path.isfile(file_path):
                            os.unlink(file_path)
                        else:
                            clear_files_from_dir(file_path)
                    except Exception, e:
                        logger.debug(e)
        clear_files_from_dir(export_tmp)

        # create player's Document and writes player's png files
        file_ = None
        try:
            file_ = open(os.path.join(export_tmp, 'doc.kml') , 'w')
            file_.write(u'<Document id="%s">\n' % player.nickname)
            file_.write(self._get_categories_as_styles(player))
            for feature in player.features:
                self._logger.debug("Feature: %s", feature)

                # get the style id for the png icon
                feature_name = feature.id[feature.id.rfind('.') + 1:]
                icon_id = player.nickname + '_' + feature_name

                # now add the feature as placemark
                file_.write(self._get_feature_as_placemark(feature, icon_id))
            file_.write(u'</Document>\n')
            file_.close()
        except Exception, e:
            if file_:
                file_.close()
            raise

        return export_tmp

    def export_to_kmz(self, player):
        """
        Exports the given player to a KMZ file.

        @param player: the player to export.
        """
        from datetime import datetime
        kmz_path = os.path.join(os.path.abspath('../../../'), '%s_%s.kmz' %
                                                (datetime.now().isoformat(),
                                                 player.nickname))

        kmz_path = kmz_path.replace(':', '_')
        export_path = self.export_to_kml(player)
        self._logger.debug(export_path)
        utils.create_zip(export_path, '', kmz_path)

        alert = NotifyAlert()
        alert.props.title = _('Export')
        alert.props.msg = _('KMZ export written to %s.' % kmz_path)
        self.view.activity.add_alert(alert)
        alert.connect('response', self.dismiss_alert_cb)

    def dismiss_alert_cb(self, alert, response_id):
        self.view.activity.remove_alert(alert)

    def __export_game_to_kmz(self):
        """
        Implemented callback method to export data of interest.

        Only the initiator will be able to export data (including
        the data within the collaborative datastructure).
        """
        path = os.path.join(constants.BUNDLE_PATH, 'geotagplugin/export')
        kmz_path = os.path.join(constants.BUNDLE_PATH,
                                'geotagplugin/%s_geotagging_export.kmz' %
                                datetime.now().isoformat())
        file_ = None
        try:
            file_ = open(path, 'w')
            file_.write(u'<?xml version="1.0" encoding="UTF-8"?>\n')
            file_.write(u'<kml>')
            for name in self.players.keys:
                player = self.players[name]
                file_.write(self.export_to_kml(player))
            file_.write(u'</kml>')
        except:
            if file_:
                file_.flush()
                file_.close()
            else:
                raise

        raise NotImplementedError # XXX TODO implmente

###############################################################################
