"""@brief The applications main module."""
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
# PURPOSE.  See the GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program (see gnu-gpl v2.txt).  If not, write to the
# Free Software Foundation, Inc., 59 Temple Place - Suite 330, Boston,
# MA 02111-1307, USA or visit the Free Software Foundation web page,
# http://www.fsf.org.
#
# @author: Henning Bredel
# Created: Oct 17, 2009
# Modified: $Date$
#       by: $Author: $
#
#endif
__version__ = '$Id $'
import os
import sys
import imp
import gtk
import glob
import time
import thread
import gobject
import logging
import traceback

from os import path
from sugar import profile
from sugar import logger
from sugar.activity.activity import Activity
from sugar.presence import presenceservice

import constants
import position
import groupthink

from utils import _
from plugin import ActionProvider
from position import GPSReceiver
from geomodel import GeoModel
from geomodel import Player
from groupthink.sugar_tools import GroupActivity
from groupthink.groupthink_base import UnorderedHandler
from shapely.geometry import Point

SERVICE = "org.n52.olpc.GeoActivity"
IFACE = SERVICE
PATH = "/org/n52/olpc/PluginSync"

###############################################################################

class GeoActivity(GroupActivity):#IGNORE:R0904,R0901
    """The Geo Activity class.

    Creates the Activities user interface and starts the Geo application.
    """

    __gsignals__ = {'position_changed': (gobject.SIGNAL_RUN_LAST,
                                         gobject.TYPE_NONE,
                                         (gobject. TYPE_PYOBJECT,))
         }

    gps_info = {
        'latitude'  : 0.0,  # WGS84 latitude
        'longitude' : 0.0,  # WGS84 longitude
        'utc'       : None, # UTC time
        'altitude'  : 0.0,  # m over sealevel
        'eph'       : 0.0,  #
        'epv'       : 0.0,  #
        'speed'     : 0.0,  # current speed
        'climb'     : 0.0,  #
        'satellites': 0     # satellites
    }

    model = None

    def __init__(self, handle):
        super(GeoActivity, self).__init__(handle)
        # share which plugin was chosen
        self.loaded_plugin = groupthink.Recentest('') # the name of the plugin
        self.loaded_plugin.HANDLER_TYPE = UnorderedHandler
        self.cloud.loaded_plugin = self.loaded_plugin

        logger.set_level('debug') # set global sugar debug level
        self._logger = logging.getLogger('geoactivity.GeoActivity')
        self._logger.setLevel(logging.DEBUG)
        self._logger.debug("Starting Geo Activity ...")

        # initialize GPS
        self.gps_position = None # set by timeout
        try:
            # setup GPS timer
            self.gps_receiver = GPSReceiver(self.gps_info)
            self._logger.debug('try to establish connection')

            #_LOG.debug("GPS_SESSION: %s", self.gps_receiver.GPS_SESSION)
            if self.gps_receiver.GPS_SESSION is not None:
                self.gps_receiver.get_position()
                gobject.timeout_add(constants.GPS_LOOP, self._emit_position_change)
                self._logger.debug('GPS connection established.')
        except:
            # no connection could be established
            self.gps_receiver.GPS_SESSION = None #IGNORE:W0702
            self._logger.warning('Could not initialize GPS session.')

        # recognize available plugins
        self._plugin_modules = _load_plugins()
        self.toolbox.set_sensitive(False)

    ############################## GUI METHODS ############################

    def initialize_display(self):
        if not self._shared_activity:
            # lets choose a plugin
            scrolled = gtk.ScrolledWindow()
            choose_plugins = self._choose_plugin_widget()
            scrolled.add_with_viewport(choose_plugins)
            return scrolled
        else:
            # lets join the plugin session
            self._logger.debug('ask which plugin is in use')

            import threading
            class JoinSession(threading.Thread):
                def __init__(self, initialize_plugin):
                    threading.Thread.__init__(self, target=initialize_plugin)

            join_session = JoinSession(self._initialize_plugin_session)
            join_session.start()

    def _choose_plugin_widget(self):
        """Returns a table from where one of the plugins can be chosen from.

        @return: Viewport containing table with plugin start buttons and
                      descriptions.
        """
        # init table for buttons
        count_plugins = len(ActionProvider.plugin_clss)
        choosing_table = gtk.Table(2, count_plugins + 1)
        choosing_table.attach(gtk.Label(_('Choose Geo-activity')), \
                  left_attach=0, right_attach=1, top_attach=0, bottom_attach=1,\
                  xpadding=10, ypadding=10)
        choosing_table.attach(gtk.Label(_('Description')), \
                  left_attach=1, right_attach=2, top_attach=0, bottom_attach=1,\
                  xpadding=10, ypadding=10)

        for i in range(1, count_plugins + 1):
            cls = ActionProvider.plugin_clss[i - 1]
            button = gtk.Button(cls.TITLE) # TODO add images here
            description = gtk.Label(cls.DESCRIPTION)
            button.connect("clicked", self._initialize_plugin_cb, cls)

            # fill entries
            choosing_table.attach(button, \
                                  left_attach=0, right_attach=1, \
                                  top_attach=i, bottom_attach=i+1,\
                                  xpadding=10, ypadding=10)
            choosing_table.attach(description, \
                                  left_attach=1, right_attach=2, \
                                  top_attach=i, bottom_attach=i+1, \
                                  xpadding=10, ypadding=10)

        viewport = gtk.Viewport()
        viewport.add(choosing_table)

        return viewport

    def _initialize_plugin_session(self):
        time.sleep(2) # let's wait for network delays

        # Search and initialize the appropriate plugin
        plugin = self.loaded_plugin.get_value()
        self._logger.debug('The shared plugin %s.', plugin)
        classes = ActionProvider.plugin_clss
        self._logger.debug('Search appropriate plugin in %s.', classes)
        for cls in classes:
            self._logger.debug('check %s' % cls)
            if plugin == cls.__module__:
                self._initialize_plugin_cb(None, cls)
                break
        else:
            # fall thorugh: no appropriate plugin found
            # TODO alert and/or exit
            self._logger.error('No appropriate plugin found.')


    def _initialize_plugin_cb(self, button, cls):
        """Creates and sets the plugin to be run.

        @param button: The button which was clicked.
        @param cls: The plugin class to be instantiated.
        """
        self.plugin = cls(self)
        title = self.plugin.TITLE
        self.loaded_plugin.set_value(self.plugin.__module__)
        self.toolbox.set_sensitive(True)
        self._logger.debug("Plugin %s created: %s" % (title, cls))

    def set_view(self, canvas):
        """Sets and shows the given canvas.

        @param canvas: The canvas the application shall set and show.
        """
        self.set_canvas(canvas)

    ############################ GET/SET METHODS ##########################

    def set_model(self, geo_model):
        """
        Sets the geo model to be accessible via activity.
        """
        self.model = geo_model

    def get_model(self):
        """
        Returns model corresponding to the activity.
        """
        return self.model

    def get_player(self):
        """
        Convenience method to return the own player.
        """
        return self.model.players[self.model.mynickname]


    ############################## GPS METHODS ############################

    def has_gps_connection(self):
        """Indicates if a GPS receiver is available or not."""
        if self.gps_receiver.GPS_SESSION is not None:
            return True
        else:
            return False

    def get_gps_position(self):
        return Point(self.gps_info['longitude'], self.gps_info['latitude'])

    def get_gps_herror(self):
        return self.gps_info['eph']

    def _emit_position_change(self):
        """
        Emits a 'position_changed' signal indicating the GPS position has
        been updated.

        Connect to with
            GeoActivity.connect(self, activity, position)
        Where position is of type L{shapely.geometry.Point}.
        """
        if self.has_gps_connection():
            self.gps_receiver.get_position()
            self.gps_position = Point(self.gps_info['longitude'],
                                      self.gps_info['latitude'])
            if self.gps_position.x != 0 and self.gps_position.y != 0:
                # (0,0) is special case
#                self._logger.debug("position changed: %s", self.gps_position)
                self.emit('position_changed', self.gps_position)
        else:
            self._logger.info('No GPS connection. Reset position to None.')
            self.gps_position = None
        #self._logger.debug('lon/lat: %s/%s' % (self.gps_position.x, self.gps_position.y))
        return True

    #######################################################################

###############################################################################

# register signal emitter
gobject.type_register(GeoActivity)

###############################################################################

_LOG = logging.getLogger('geoactivity')
def _load_plugins():
    """Initializes all plugins laying in ${app_path}/${plugin_loc} directory.

    @return: A list containing all loaded modules.
    """
    plugin_dir = path.abspath('.')
    _LOG.debug('Searching for plugin submodules.')

    # Load all available plugins. We only load modules laying within its
    # own package (without submodules).
    plugin_names = [file_ for file_ in os.listdir(plugin_dir) if \
                    (path.isdir(file_) or path.islink(file_)) and \
                    str(file_).endswith('plugin')]
    _LOG.debug('plugins found: %s' % plugin_names)

    # load the plugin module (the first module ending on '*plugin.py'
    modules = [glob.glob1(path_, '*plugin.py') for path_ in plugin_names]
    module_names = [[ps[:-3] for ps in ms] for ms in  modules if len(ms) != 0]
    return [_load_module(mod.pop(), plugin_names) for mod in module_names]

def _load_module(name, plugin_paths=None):
    """Dynamically loads a module from the plugin directory.

    The module to load must lay in the plugin directory. Make sure
    the plugin.py contains a class inheriting the AbstractPlugin class.

    @param name: The location of the module to load.
    @param plugin_paths: A list of namespaces where to search.
    @return The loaded module.

    @exception IOError: If the module could not be found or read.
    @exception ImportError: If the module could not be imported.
    """
    file_ = None
    try:
        try:
            _LOG.debug('Loading module %s %s' % (name,  '...'))
            __import__(name)
            file_, path, description = imp.find_module(name, plugin_paths)
            module = imp.load_module(name, file_, path, description)
            #_LOG.debug("%s\'s SCOPE %s" %(name, dir(module)))
            return module
        finally:
            try:
                if file_:
                    file_.close()
            except IOError:
                _LOG.warn('Could not load plugin %s' % name)
                traceback.print_exc(file=sys.stderr)
    except ImportError:
        _LOG.warn('Could not import plugin %s' % name)
        traceback.print_exc(file=sys.stderr)
        raise
    except:
        _LOG.warn('Unexpected error occured while loading module %s' % name)
        traceback.print_exc(file=sys.stderr)
        raise

###############################################################################

#if __name__ == '__main__':
#    plugin_dir = path.abspath('.')
#    LOGGER.debug('Searching for plugin submodules.')
#
#    # Load all available plugins. We only load modules laying within its
#    # own package (without submodules).
#    print os.listdir(plugin_dir)
#    pkg_names = [file_ for file_ in os.listdir(plugin_dir) if \
#                   path.isdir(path.join(plugin_dir, file_))  or \
#                   path.islink(path.join(plugin_dir, file_)) and \
#                   str(plugin_dir).endswith('plugin')]
#    plugin_paths = [path.join(plugin_dir, plugin) for plugin in pkg_names]
#
#    # load the plugin module (the first module ending on '*plugin.py'
#    modules = [glob.glob1(path_, '*plugin.py') for path_ in plugin_paths]
#    module_names = [[ps[:-3] for ps in ms] for ms in  modules]
#    mods = [mod for mod in module_names if  len(mod) != 0]
#    psst = [__load_module(mod.pop(), plugin_paths) for mod in mods]
#    logging.debug(psst)
#    print [plugin.title for plugin in ActionProvider.plugin_clss]