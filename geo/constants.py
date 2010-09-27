"""Contains constant values."""
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
# Created: Dec 4, 2009
# Modified: $Date$
#       by: $Author: $
#
#endif
__version__ = '$Id: constants.py 118 2010-03-25 13:56:42Z  $'
import os
import logging

from sugar.activity import activity

# GLOBAL LOGGING
LOG_LEVEL = logging.DEBUG

# PATHS
BUNDLE_PATH = activity.get_bundle_path()
CONFIG_PATH = os.path.join(BUNDLE_PATH, 'config')
ICON_PATH = os.path.join(BUNDLE_PATH, 'icons')
TMP_PATH = os.path.join(BUNDLE_PATH, 'tmp')

# VALUES
GPS_LOOP = 2000 # repeat GPS retrieval in milliseconds
SPACE_DISCRETION = 0.00003 # buffer (assume two points to be equal) XXX test

# GeoJSON IDs
PLAYER_ID = 'org.n52.olpc.player'
PLAYER_POSITION_ID = PLAYER_ID + '.position'
PLAYER_TRACE_ID = PLAYER_ID + '.trace'
PLAYER_FEATURE_ID = PLAYER_ID + '.feature'
FEATURE_ID = 'org.n52.olpc.feature'
