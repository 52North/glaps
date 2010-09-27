"""@brief Main classes and functions for the geotag plugin."""
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
__version__ = '$Id $'
import os
import sys
import gtk
import time
import math
import gobject
import logging

from sugar import profile
from sugar.graphics.radiotoolbutton import RadioToolButton
from sugar.graphics.toggletoolbutton import ToggleToolButton
from sugar.graphics.toolbutton import ToolButton

import geotagmodel
import constants
import geojson
import utils

from utils import _
from plugin import ActionProvider
from shapely.geometry import Point
from osmtileview import OSMTileView
from utils import addto_icon_path

NONE_CATEGORY = 'none'

###############################################################################

class GeoTag(ActionProvider):
    """
    TODO classdocs geotag
    """

    __gsignals__ = {'position_changed': (gobject.SIGNAL_RUN_LAST,
                                         gobject.TYPE_NONE,
                                         (gobject. TYPE_PYOBJECT,))
         }

    TITLE = _('GeoTagging')
    DESCRIPTION = _('Geotagging game')
    ICONS_PATH = os.path.join(constants.BUNDLE_PATH, 'geotagplugin/icons')

    center_on_first_position_handler = None

    def __init__(self, activity):
        """
        TODO Add some descritpion here.
        """
        ActionProvider.__init__(self, self.TITLE, self.DESCRIPTION,
                                os.path.join(self.ICONS_PATH, 'geotag.svg'))
        addto_icon_path(self.ICONS_PATH)
        self._logger = logging.getLogger('GetTagPlugin')

#        self.map = OSMTileView(activity)
        from wmsview import WMSView
        self.map = WMSView(activity)
        self.model = geotagmodel.GeoTagModel(activity, self.map)
        self.map.set_size_request(920, 815)
        self.model.set_size_request(280, 815)

        # add toolbars
        self.map.register_toolbars(activity.toolbox)
        control = GeoTagControl(self.model, self.map)
        activity.toolbox.set_current_toolbar(1)
        geotagtoolbar = GeoTagToolbar(control)
        geotagtoolbar.show()
        activity.toolbox.add_toolbar(_('GeoTag tools'), geotagtoolbar)

        canvas = gtk.HBox()
        canvas.pack_start(self.model)
        canvas.pack_start(self.map)

        # set the plugin canvas and show it
        activity.set_view(canvas)
        canvas.show()

        self.center_on_first_position_handler = activity.connect("position_changed",
                                                                 self.map.init_center)


###############################################################################

class GeoTagControl():

    def __init__(self, model, map):
        self._logger = logging.getLogger('GeoTagControl')
        self._logger.setLevel(constants.LOG_LEVEL)

        self.model = model
        self.map = map

        self.position = None

    def export(self, button):
        """
        Writes the current status of the player to a file.
        """
        nickname = self.model.mynickname
        player = self.model.players[nickname]
        self.model.export_to_kmz(player)

    def create_tagstar(self, toolbar):
        """
        Set the tagging toolbar. We need access to the combobox.
        """
        self._logger.debug('set_toolbar()')
        self.tag_star = TagStar(toolbar, self)
        self.map.set_size_request(920, 815)

    def show_tag_star(self):
        """
        Removes the map and shows the tag star instead. With the tagstar
        the user can create/edit tags.
        """
        self._logger.debug('show_tag_star()')

        player = self.model.players[self.model.mynickname]
        self.position = player.get_position()

        self.map.pack_start(self.tag_star)
        feature = self.model.selected_feature
        if feature:
            # set selection in tagstar if tag belongs to player
            player = self.model.players[self.model.mynickname]
            if feature in player.features:
                # id's form: `constants.PLAYER_FEATURE_ID + "." + <category>'
                id_levels = feature.id.split('.')
                category = id_levels[len(id_levels) - 1]
                self.tag_star.set_toggled(None, category)

        self.model.treeview.set_sensitive(False)
        self.map.remove(self.map.vbox)

    def remove_tag_star(self, text):
        """
        Removes the tag star and shows the map again. After removing the
        tagstar, the tagged feature is stored with the player, or -- if
        the user has edited the tag -- the will has been updated.

        @param text: Description text from the combobox to store with the
        tagged item. Won't be of interest, if tag was deleted.
        """
        self._logger.debug('remove_tag_star()')  # XXX refactor star => circle
        self.map.remove(self.tag_star)
        self.map.pack_start(self.map.vbox)
        category = self.tag_star.toggled

        # check, if s/th was tagged
        if category is not NONE_CATEGORY:
            if self.model.selected_feature:
                # edit/replace feature
                self.remove_selected_feature()
                self.tag_feature(category, text)
            else:
                # add new feature
                self.tag_feature(category, text)
        else:
            self.remove_selected_feature()

        self.model.treeview.set_sensitive(True)
        self.tag_star.reset_toggled(None)

    def remove_selected_feature(self):
        """
        Removes the currently selected feature from the model, if a
        feature was selected in the tree and the feature belongs to
        the player.
        """
        self._logger.debug("remove_selected_feature()")
        if self.model.selected_feature:
            # remove feature from player, map and model
            feature = self.model.selected_feature
            player = self.model.players[self.model.mynickname]
            if player.has_feature(feature):
                player.remove_feature(feature)

                time_stamp = feature.properties['time_stamp']
                cat_name = feature.id[feature.id.rfind('.') + 1 :]
                ref_key = cat_name + "_" + time_stamp
                self._logger.debug("ref_key for re-sync: %s", ref_key)

                feature_overlay = self.model.category_overlays[ref_key]
                self.model.remove_feature(feature_overlay, cat_name)

    def tag_feature(self, category, text):
        """
        Creates a tag at the current location with under given category
        and given description.

        @param category: One of the given ones, parsed from tag_descriptions.
        @param text: A more detailed information on the feature.
        """
        self._logger.debug('tag_feature()')
        player = self.model.players[self.model.mynickname]

        # add feature to player
        icon_name = category
        time_stamp = str(time.time())
        ref_key = category + "_" + time_stamp
        id = constants.PLAYER_FEATURE_ID + '.' + category
        feature = geojson.Feature(id, self.position, {'time_stamp': time_stamp,
                                                      'icon_name': icon_name,
                                                      'description' : text})
        player.add_feature(feature)

        # add feature to model
        (stroke, fill) = (player.color_stroke, player.color_fill)
        local_icon = os.path.join(GeoTag.ICONS_PATH, icon_name)
        overlay = get_pixbuf_from_plugin(local_icon, stroke, fill, (30, 30))
        self.model.category_overlays[ref_key] = overlay
        self.model.add_feature(overlay, self.position, category)

###############################################################################

class TagStar(gtk.HBox):
    """
    A L{gtk.HBox} which arranges togglebuttons around the current position
    within a L{gtk.Fixed} widget.

    This is the central tag element, where a user can either tag his current
    position with a category specified in L{geotagplugin.ECategory}. If
    one of the user's already tagged features is selected in the tree, the
    made change action will be handled as an edit.
    """

    IMG_SIZE = (100, 100)
    BUTTON_SIZE = (100, 100)
    EMPTY_LIST_STORE = gtk.ListStore(gobject.TYPE_STRING)

    toggled = NONE_CATEGORY # selected category
    selected = None # gtk.Image displaying selected category

    def __init__(self, toolbar, control):
        gtk.HBox.__init__(self)
        self._logger = logging.getLogger('TagStar')
        self._logger.setLevel(constants.LOG_LEVEL)
        self.toolbar = toolbar
        self.control = control

        self.size_cb = self.connect('size_allocate', self.size_allocate_cb)

        self.fixed = gtk.Fixed()
        self.pack_start(self.fixed)
        self.show_all()

    def size_allocate_cb(self, widget, event):
        """
        Builds the tag star around the center where the selected
        category is shown.
        """
        self._logger.debug('size_allocate_cb()')
        x, y, width, height = self.fixed.get_allocation()
        self._logger.debug('x: %s, y: %s, w: %s, h: %s', x, y, width, height)
        self.set_size_request(width, height)

        ######################################################################
        # place togglebuttons around the current position in a radio group

        color_fill = profile.get_color().get_fill_color()
        color_stroke = profile.get_color().get_stroke_color()
        button_width, button_height = self.BUTTON_SIZE
        cat_names = get_categories()

        radius = 300 # px
        x_center = width / 2 - 40
        y_center = height / 2 - 40
        step_angle = math.radians(360 / (len(cat_names) + 1)) # plus reset btn

        # add a reset button
        self.reset_selected_btn = RadioToolButton()
        img_name = os.path.join(GeoTag.ICONS_PATH, 'reset.svg')
        icon = gtk.image_new_from_pixbuf(utils.load_svg_image(img_name,
                                                   color_stroke,
                                                   color_fill,
                                                   self.IMG_SIZE))
        self.reset_selected_btn.set_icon_widget(icon)
        self.reset_selected_btn.set_tooltip(_('Reset selected tag.'))
        self.reset_selected_btn.connect('clicked', self.reset_toggled)
        self.reset_selected_btn.show_all()
        self.reset_selected_btn.set_size_request(button_width, button_height)
        self.fixed.put(self.reset_selected_btn,
                       x_center,          # + int(radius * math.sin(i * step_angle)),
                       y_center + radius) # + int(radius * math.cos(i * step_angle)))
        self.reset_selected_btn.set_active(False)

        # read all available categories dynamically
        for i, category in enumerate(cat_names):
            button = RadioToolButton(group=self.reset_selected_btn)
            img_name = os.path.join(GeoTag.ICONS_PATH, category)
            icon = get_gtkimage_from_plugin(img_name, color_stroke, color_fill, self.IMG_SIZE)
            button.set_icon_widget(icon)
            button.set_tooltip(_('Tag some %s.' % category))            # XXX check translation here!!
            button.connect('clicked', self.set_toggled, category)
            button.show_all()
            button.set_size_request(button_width, button_height)
            self.fixed.put(button,
                           x_center + int(radius * math.sin((i + 1) * step_angle)),
                           y_center + int(radius * math.cos((i + 1) * step_angle)))
            button.set_active(False)

        img_name = os.path.join(GeoTag.ICONS_PATH, NONE_CATEGORY)
        self._set_selected(get_gtkimage_from_plugin(img_name, color_stroke,color_fill, self.IMG_SIZE))

        ###################################################################

        self._logger.debug("size_allocation done")
        self.disconnect(self.size_cb) ## use only once

    def reset_toggled(self, button):
        """
        Resets toggled property and combobox liststore.

        @param button: The reset button (can be omitted by passing None).
        @note: If a tag was selected within the L{geotagmodel.GeotagModel},
        the tag will be deleted.
        """
        self.toggled = NONE_CATEGORY

        # reset liststore
        combo = self.toolbar.combobox
        combo.set_model(self.EMPTY_LIST_STORE)

        # reset selected widget
        color_fill = profile.get_color().get_fill_color()
        color_stroke = profile.get_color().get_stroke_color()
        self._set_selected(get_gtkimage_from_plugin(NONE_CATEGORY,
                                                    color_stroke,
                                                    color_fill,
                                                    self.IMG_SIZE))

        self.reset_selected_btn.set_active(True)
        self.selected.queue_draw()
        combo.queue_draw()

    def set_toggled(self, button, category):
        """
        Switches the empty Button and the tagged category button clicked.
        Also, sets the appropriate liststore for the combobox.

        @param button: Toggled button (can be omittted).
        @param category: The corresponding category to set.
        """
        self._logger.debug("set_toggled()")

        self.toggled = category

        # set liststore
        combo = self.toolbar.combobox
        combo.set_model(self.toolbar.description_sets[category])

        color_fill = profile.get_color().get_fill_color()
        color_stroke = profile.get_color().get_stroke_color()

#        self._logger.debug("storage type: %s", self.selected.get_property("storage-type"))
        self._set_selected(get_gtkimage_from_plugin(category,
                                                    color_stroke,
                                                    color_fill,
                                                    self.IMG_SIZE))
        combo.queue_draw()

    def _set_selected(self, widget):
        """
        Sets the widget as the currently selected tag category.

        @param widget: The L{gtk.Image} to set.
        """
        x, y, width, height = self.fixed.get_allocation()
        x_center = width / 2 - 40
        y_center = height / 2 - 40

        if self.selected:
            self.selected.clear()
        button_width, button_height = self.BUTTON_SIZE
        widget.set_size_request(button_width, button_height)
        widget.show_all()
        self.selected = widget
        self.selected.queue_draw()

        self.fixed.put(self.selected, x_center, y_center)

###############################################################################

class GeoTagToolbar(gtk.Toolbar):
    """
    Contains tools to categorize observations and add them to the map.
    """

    def __init__(self, control):
        """
        Creates the tagging toolbar with tag button and description combo.

        The textfield combo suggests a default description for the chosen
        category.

        For now the following categories are present:
         - agriculture
         - animal
         - building
         - infrastructure
         (- photo)
         - text
         - vegetation
         - water

        Get each description as gtk.Liststore:
            GeoTagToolbar.description_sets[category]
        """
        gtk.Toolbar.__init__(self)
    	self._logger = logging.getLogger('GeoTagToolbar')
    	self._logger.setLevel(constants.LOG_LEVEL)
        self.control = control
        self.control.create_tagstar(self)

        # holds default descriptions for each category
        self.description_sets = dict()

        # get and parse each description set
        file_ = None
        try:
            desc_path = os.path.join(constants.BUNDLE_PATH, 'geotagplugin/tag_descriptions')
            for description_set in get_categories():
                # parse default descriptions into liststore
                path = os.path.join(desc_path, description_set)
                file_ = open(path, 'r')
                liststore = gtk.ListStore(gobject.TYPE_STRING)
                for description in file_.readlines():
                    if not description.startswith('#'):
                        liststore.append([description.strip()])
                #self._logger.debug('key: %s', files[i])
                self.description_sets[description_set] = liststore
        except IOError:
            self._logger.error("Failed reading categories.")
            raise
        finally:
            if file_:
                file_.close()

        self.store_player_btn = ToolButton('kmz-export')
        self.store_player_btn.set_tooltip(_('Export player data.'))
        self.store_player_btn.connect('clicked', self.control.export)
        self.insert(self.store_player_btn, -1)
        self.store_player_btn.show()

        self.export_csv = ToolButton('csv-export')
        self.export_csv.set_tooltip(_('Export to CSV.'))
        self.export_csv.connect('clicked', self.control.model.export_to_csv)
        self.export_csv.show()
        self.insert(self.export_csv, -1)

        separator = gtk.SeparatorToolItem()
        separator.set_draw(False)
        separator.set_expand(True)
        self.insert(separator, -1)
        separator.show()

        # add tag-toggled-category button
        self.tag_star_btn = ToggleToolButton('activity-start')
        self.tag_star_btn.set_tooltip(_('Tag something!'))
        self.tag_star_btn.connect('clicked', self._toggle_tag_star)
        self.insert(self.tag_star_btn, -1)
        self.tag_star_btn.show()

        # create textfieldcombo for default descriptions
        self.combobox = gtk.combo_box_entry_new_text()
        toolitem = gtk.ToolItem()
        toolitem.add(self.combobox)
        toolitem.set_size_request(600, 20)
        self.combobox.set_property('sensitive', False)
        self.combobox.show()
        self.insert(toolitem, -1)
        toolitem.show()

    def _toggle_tag_star(self, button):
        """
        Makes controller show/remove the tag star.
        """
        self._logger.debug('_toggle_tag_star()')
        if self.tag_star_btn.get_active():
            self.combobox.set_property('sensitive', True)
            self.control.show_tag_star()
        else:
            self.combobox.set_property('sensitive', False)
            text = self.combobox.get_active_text()
            self.control.remove_tag_star(text)

###############################################################################

def get_categories():
    """
    Scans the tag_description folder and returns a list of categories. Each
    tag_description indicates a category.

    @return: A list of categories available.
    """
    path = os.path.join(constants.BUNDLE_PATH, 'geotagplugin/tag_descriptions')
    cat_names = os.listdir(path)
    for file in cat_names:
        # skip folders and hidden files
        if os.path.isdir(os.path.join(path, file)) or file.startswith('.'):
            cat_names.remove(file)
    return cat_names

def get_gtkimage_from_plugin(name, stroke, fill, size=(20,20)):
    """
    Creates a L{gtk.Image} from given name of an svg-icon within this plugin.

    @param name: The name (without svg postfix) of the file.
    @param stroke: The fill color as hex string.
    @param fill: The stroke color as hex string.
    @param size: The size of the image.
    """
    img_name = os.path.join(GeoTag.ICONS_PATH, name + '.svg')
    pixbuf = get_pixbuf_from_plugin(name, stroke, fill, size)
    return gtk.image_new_from_pixbuf(pixbuf)

def get_pixbuf_from_plugin(name, stroke, fill, size=(20, 20)):
    """
    Creates a L{gtk.gdk.Pixbuf} from the given name of an svg-icon.

    @param name: The full path of the file.
    @param stroke: The fill color as hex string.
    @param fill: The stroke color as hex string.
    @param size: The size of the image.
    """
    icon_path = os.path.join(GeoTag.ICONS_PATH, name + '.svg')
    return utils.load_svg_image(icon_path, stroke, fill, size)
