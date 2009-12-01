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
__version__ = '$Id: $'
import gtk
import logging

#import gettext
#gettext.bindtextdomain('myapplication', './po')
#gettext.textdomain('myapplication')
#_ = gettext.gettext
#
#print _('This is a translatable string.')

from utils import _
from utils import init_logging
from wmsview import WMSView
from osmtileview import OSMTileView
from model import GeospaceModel
from plugin import ActionProvider

LOGGER = logging.getLogger('geocacheplugin-logger')
init_logging(LOGGER)
###############################################################################

class GeoCache(ActionProvider):
    """
    classdocs
    """
    title = _('GeoCache')
    description = _('Find things hidden at a secret place.')
    img_path = 'img/plugin-geocache.svg'

    def __init__(self, geospace_activity, toolbox):
        """Constructor.

        XXX Add description here
        """
        ActionProvider.__init__(self, geospace_activity, self.title, \
                                self.description, self.img_path)

        # XXX add toolbar to switch views
        # XXX add model
        self.model = GeospaceModel()

        #self.map = WMSView(geospace_activity)
        self.map = OSMTileView(geospace_activity)
        self.map.register_toolbars(toolbox)
        toolbox.set_current_toolbar(1)

        canvas = gtk.HPaned()
        canvas.pack1(self.model)
        canvas.pack2(self.map)
        canvas.show_all()

        # call the plugin_register method of the activity
        geospace_activity.set_view(canvas)

    def on_size_allocate(self, widget, allocation):
        rect = widget.get_parent().get_allocation()
        LOGGER.debug('main canvas allocation: %sx%s, at (%s,%s)' % \
                     (rect.width, rect.height, rect.x, rect.y))
        LOGGER.debug('widget size allocation: %sx%s, at (%s,%s)' % \
                     (allocation.width, allocation.height, \
                     allocation.x, allocation.y))

    def start(self):
        """Starting the plugin action."""
        raise NotImplementedError

    def stop(self):
        """Stopping the plugin action."""
        raise NotImplementedError

###############################################################################
