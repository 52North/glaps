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
__version__ = '$id $'
import os
import sys
import imp
import gtk
import glob
import logging
import logging.config
import traceback

from os import path

from sugar.activity.activity import Activity
from sugar.activity.activity import ActivityToolbox

import utils

from utils import _
from plugin import ActionProvider

LOGGER = logging.getLogger('geospace-logger')

###############################################################################

class GeoSpaceActivity(Activity):#IGNORE:R0904,R0901
    """The GeoSpace Activity class.

     Creates the Activities user interface and starts the GeoSpace application.
     """

    def __init__(self, handle):
        """Constructor."""
        Activity.__init__(self, handle)

        self.plugin = None

        utils.init_logging(LOGGER)
        LOGGER.debug("Starting GeoSpace Activity ...")
        LOGGER.debug('The library path: %s ' % sys.path)

        toolbox = ActivityToolbox(self)

        # recognize plugins available and make them choosable
        self._plugin_modules = _load_plugins()
        choose_plugins = self._plugin_choosing_widget(toolbox)
        scrolled = gtk.ScrolledWindow()
        scrolled.add_with_viewport(choose_plugins)
        scrolled.show_all()
        self.set_canvas(scrolled)

        self.set_toolbox(toolbox)
        toolbox.show()

    def _plugin_choosing_widget(self, toolbox):
        """Returns a table from where one of the plugins can be chosen from.

        @param toolbox: The activitys toolbox.
        @return: Viewport containing table with plugin start buttons and
                      descriptions.
        """
        # init table
        count_plugins = len(ActionProvider.plugin_clss)
        choosing_table = gtk.Table(2, count_plugins + 1)
        choosing_table.attach(gtk.Label(_('Choose geo-activity')), \
                  left_attach=0, right_attach=1, top_attach=0, bottom_attach=1, \
                  xpadding=10, ypadding=10)
        choosing_table.attach(gtk.Label(_('Description')), \
                  left_attach=1, right_attach=2, top_attach=0, bottom_attach=1, \
                  xpadding=10, ypadding=10)

        for i in range(1, count_plugins + 1):
            cls = ActionProvider.plugin_clss[i - 1]
            button = gtk.Button(cls.title)
            description = gtk.Label(cls.description)
            button.connect("clicked", self.initialize_plugin_cb, cls, toolbox)

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

    def set_view(self, canvas):
        """Sets and shows the given canvas.

        @param canvas: The canvas the application shall set and show.
        """
        self.set_canvas(canvas)

    def initialize_plugin_cb(self, button, cls, toolbox):
        """Creates and sets the plugin to be run.

        @param button: The button which was clicked.
        @param cls: The plugin class to be instantiated.
        @param toolbox: The Activitys toolbox to a plugin can add its own.
        """
        self.plugin = cls(self, toolbox)
        LOGGER.debug("Plugin %s created: %s" % (self.plugin.title, cls))

    def write_file(self, file_path):
        """Writes state to journal. Not implemented yet."""
        raise NotImplementedError

    def read_file(self, file_path):
        """Reads state from journal. Not implemented yet."""
        raise NotImplementedError

###############################################################################

def _load_plugins():
    """Initializes all plugins laying in ${app_path}/${plugin_loc} directory.

    @return: A list containing all loaded modules.
    """
    plugin_dir = path.abspath('.')
    LOGGER.debug('Searching for plugin submodules.')

    # Load all available plugins. We only load modules laying within its
    # own package (without submodules).
    pkg_names = [file_ for file_ in os.listdir(plugin_dir) if \
                   path.isdir(path.join(plugin_dir, file_))  or \
                   path.islink(path.join(plugin_dir, file_)) and \
                   str(plugin_dir).endswith('plugin')]
    plugin_paths = [path.join(plugin_dir, plug) for plug in pkg_names]

    # load the plugin module (the first module ending on '*plugin.py'
    modules = [glob.glob1(path_, '*plugin.py') for path_ in plugin_paths]
    module_names = [[ps[:-3] for ps in ms] for ms in  modules if len(ms) != 0]
    return [_load_module(mod.pop(), plugin_paths) for mod in module_names]

def _load_module(name, pkg_path=None):
    """Dynamically loads a module from the plugin directory.

    The module to load must lay in the plugin directory. Make sure
    the plugin.py contains a class inheriting the AbstractPlugin class.

    @param name: The location of the module to load.
    @param pkg_path: A list of namespaces where to search.
    @return The loaded module.

    @exception IOError: If the module could not be found or read.
    @exception ImportError: If the module could not be imported.
    """
    file_ = None
    try:
        try:
            LOGGER.debug('Loading module %s %s' % (name,  '...'))
            file_, filename, description = imp.find_module(name, pkg_path)
            return imp.load_module(name, file_, filename, description)
        finally:
            try:
                if file_:
                    file_.close()
            except IOError:
                LOGGER.warn('Could not load plugin %s' % name)
                traceback.print_exc(file=sys.stderr)
    except ImportError:
        LOGGER.warn('Could not import plugin %s' % name)
        traceback.print_exc(file=sys.stderr)
        raise
    except:
        LOGGER.warn('Unexpected error occured while loading module %s' % name)
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