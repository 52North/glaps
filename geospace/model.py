"""Module representing common data."""
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

import gtk

class GeospaceModel(gtk.VBox):
    """Model containing general data.

    XXX put in data needed for collaboration scenarios
    XXX interface for import/export
    XXX as descriptor class ? ( __get__ __set__)
    """

    def __init__(self, ):
        """
        Constructor
        """
        gtk.VBox.__init__(self)
        self.set_size_request(150, 750)