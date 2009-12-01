"""Module for work with general (georeferenced) rasters."""
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
__version__ = '$Id: $'

import logging

from utils import _
from utils import init_logging
from geospace import GeospaceCanvas
from geospace import GeospaceToolbar

LOGGER = logging.getLogger('raster-logger')
init_logging(LOGGER)

###############################################################################

class RasterView(GeospaceCanvas):
    """View for showing (georeferenced) raster files, like scanned maps."""

    def __init__(self, parent_window):
        GeospaceCanvas.__init__(self)

    def get_toolbar(self):
        """Method wherein a RasterView instance can register its toolbars."""

###############################################################################

class _RasterToolbar(GeospaceToolbar):
    """Controller for the raster view."""

    name = _('Raster Tools')

    def __init__(self):
        GeospaceToolbar.__init__(self, self.name)

        self.enable_zoom_in(self.zoom_in_cb)
        self.enable_zoom_out(self.zoom_out_cb)
        self.enable_zoom_bestfit(self.zoom_best_fit_cb)

    def zoom_in_cb(self, button):
        """Zoom in the map.""" #XXX how to implement zoom in?
        LOGGER.debug('zoom in pressed')
        raise NotImplementedError

    def zoom_out_cb(self, button):
        """Zoom out the map.""" #XXX how to implement zoom out?
        LOGGER.debug('zoom out pressed')
        raise NotImplementedError

    def zoom_best_fit_cb(self, button):
        """Zoom the map extent to best fit.""" #XXX how to define best fit?
        LOGGER.debug('best fit pressed')
        raise NotImplementedError