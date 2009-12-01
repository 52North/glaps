"""@brief Defines plugin mechanism.

    The plugin architecture adopts the mechanism described by
    Marty Alchin on his Weblog 2008-01-10. Have a look at
    @see: http://martyalchin.com/2008/jan/10/simple-plugin-framework/
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
# Created: Oct 25, 2009
# Modified: $Date$
#       by: $Author: $
#
#endif
__version__ = '$id $'
import gtk
import logging

import utils

LOGGER = logging.getLogger('action-provider-logger')
utils.init_logging(LOGGER) #IGNORE:E1101

###############################################################################

class PluginMount(type):
    """
    Providing the neutral location for plugin and application.
    """
    def __init__(mcs, name, bases, attrs):
        type.__init__(mcs, name, bases, attrs)
        if not hasattr(mcs, 'plugin_clss'):
            # This branch only executes when processing the mount point itself.
            # So, since this is a new plugin type, not an implementation, this
            # class shouldn't be registered as a plugin. Instead, it sets up a
            # list where plugins can be registered later.
            LOGGER.debug('Initializing mount point for plugins: %s' % mcs)
            mcs.plugin_clss = []
        else:
            # This must be a plugin implementation, which should be registered.
            # Simply appending it to the list is all that's needed to keep
            # track of it later.
            LOGGER.debug('New action provider class (plugin): %s' % mcs)
            mcs.plugin_clss.append(mcs)

###############################################################################

class ActionProvider():
    """Mount point for plugins which refer to actions that can be performed.

    Plugins implementing this reference should provide the following attributes:

    =======  =========================================
    activitiy     The activity instance where the plugin is running in.

    title         The text to be displayed, describing the action.

    description   The description which gives more information about the plugin.

    img_path      The path to an image representing the plugin.
    =======  =========================================

    You have to implement the abstract methods provided, so the framework
    can handle the plugin.
    """
    __metaclass__ = PluginMount

    def __init__(self, activity, title, description, img_path):
        """Sets descriptive metadata of the plugin.

        @param activity: The activity instance.
        @param title: The title of the plugin.
        @param description: A small but pregnant description.
        @param img_path: The path to the Image.
        @exception ValueError: If one of the parameters is None.
        """
        if activity is None or title is None or \
           description is None or img_path is None:
            LOGGER.warn('Missing either activity/title/description/img_path!')
            raise ValueError

        self.parent = activity
        self.title = title
        self.description = description
        self.img_path = img_path

    def start(self):
        """Abstract method."""
        raise NotImplementedError

    def stop(self):
        """Abstract method."""
        raise NotImplementedError

###############################################################################
