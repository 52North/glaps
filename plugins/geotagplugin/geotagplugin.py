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
__version__ = '$id $'
import gtk

from utils import _
from plugin import LOGGER
from plugin import ActionProvider

###############################################################################

class GeoTag(ActionProvider):
    '''
    classdocs
    '''

    title = _('GeoTagging')
    description = _('Geotagging game')
    img_path = 'img/plugin-geotag.svg'

    def __init__(self, geospace_activity, toolbox):
        ActionProvider.__init__(self, geospace_activity, self.title, \
                                self.description, self.img_path)
        self.parent = geospace_activity

        # initialize plugin stuff (toolbars etc)
        # call the plugin_register method of the activity

    def start(self):
        """Starting the plugin action."""
        raise NotImplementedError

    def stop(self):
        """Stopping the plugin action."""
        raise NotImplementedError

###############################################################################
