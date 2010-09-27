"""@brief Contains some utility methods."""
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
# Author: Henning Bredel
# Created: Oct 17, 2009
# Modified: $Date$
#       by: $Author: $
#
#endif
__version__ = '$id $'
import os
import re
import gtk
import rsvg
import cairo
import zipfile
import logging
import logging.config
import telepathy

from gettext import gettext
from sugar import profile

import constants

rsvg.set_default_dpi(300)
LOGGER = logging.getLogger('utils-logger')
_DEFAULT_LOG_LEVEL = logging.DEBUG


###############################################################################

def get_buddy_from_handle(activity, cs_handle):
    """
    Returns Buddy object for the given DBUS handle.

    @param activity: The own activity running.
    @param cs_handle: The DBUS handle string.
    """
    LOGGER.debug('Trying to find owner of handle %u...', cs_handle)
    group = activity.text_chan[telepathy.CHANNEL_INTERFACE_GROUP]
    my_csh = group.GetSelfHandle()
    LOGGER.debug('My handle in that group is %u', my_csh)

    conn = activity._shared_activity.telepathy_conn
    if my_csh == cs_handle:
        handle = conn.GetSelfHandle()
        LOGGER.debug('CS handle %u belongs to me, %u', cs_handle, handle)
    elif group.GetGroupFlags() & telepathy.CHANNEL_GROUP_FLAG_CHANNEL_SPECIFIC_HANDLES:
        handle = group.GetHandleOwners([cs_handle])[0]
        LOGGER.debug('CS handle %u belongs to %u', cs_handle, handle)
    else:
        handle = cs_handle
        LOGGER.debug('non-CS handle %u belongs to itself', handle)
        # XXX: deal with failure to get the handle owner
        assert handle != 0
    return activity.pservice.get_buddy_by_telepathy_handle(
        conn.service_name, conn.object_path, handle)

###############################################################################

def get_xo_icon(color_stroke=None, color_fill=None, size=(20,20)):
    """
    @param color_stroke: The stroke color as hex string (default is players stroke).
    @param color_fill: The fill color as hex string (default is players fill).
    @param size: A tupel of size in pixels: (width,height).
    @return: The XO icon with given colors and size
    """
    if (color_stroke == None) or (color_fill == None):
        color_stroke = profile.get_color().get_stroke_color()
        color_fill = profile.get_color().get_fill_color()
    name = os.path.join(constants.BUNDLE_PATH, 'icons/computer-xo.svg')
    return load_svg_image(name, color_stroke, color_fill, size)

def load_svg_image(name, color_stroke, color_fill, size=(20,20)):
    """
    Loads the given SVG file and returns it as colorified pixbuf.

    @param color_stroke: The stroke color as hex string.
    @param color_fill: The fill color as hex string.
    @param size: Tuple of size in pixels: (width,height).
    @return: The colored image as L{gtk.gdk.pixbuf}.
    """
    file_ = open(name, 'r')
    svg_data = file_.read()
    file_.close()

    color_svg = load_svg(svg_data, color_fill, color_stroke)
    pixbuf_loader = gtk.gdk.PixbufLoader('svg')
    pixbuf_loader.set_size(size[0], size[1])
    pixbuf_loader.write(color_svg)
    pixbuf_loader.close()
    return pixbuf_loader.get_pixbuf()

def load_svg(svg, color_stroke=None, color_fill=None):
    """
    Returns an SVG handle.

    @param svg: The SVG image file.
    @param color_stroke: The XO stroke color.
    @param color_fill: The XO fill color.
    @param size: The size of the image, tupel of (widht, height).
    """
    if ((color_stroke == None) or (color_fill == None)):
        return svg #rsvg.Handle(data=svg)

    # replace color entities
    entity = '<!ENTITY fill_color "%s">' % color_fill
    svg = re.sub('<!ENTITY fill_color .*>', entity, svg)
    entity = '<!ENTITY stroke_color "%s">' % color_stroke
    svg = re.sub('<!ENTITY stroke_color .*>', entity, svg)

    return svg #rsvg.Handle(data=svg)

def addto_icon_path(path):
    """
    Adds the given path to the look-up path of the default icon theme.
    """
    LOGGER.debug('Adding icon path to search path: %s', path)
    icon_theme = gtk.icon_theme_get_default()
    icon_theme.append_search_path(path)

###############################################################################

def zip_folder(path, relname, archive):
    """
    Walks recursively through the path and adds files and directories to
    the zip folder.

    @param path: The folder's path to zip.
    @param relname: The relative path where to place contents within the zip.
    @param archive: The archive's zip file name.
    """

    paths = os.listdir(path)
    for p in paths:
        p1 = os.path.join(path, p)
        p2 = os.path.join(relname, p)
        if os.path.isdir(p1):
            zip_folder(p1, p2, archive)
        else:
            archive.write(p1, p2)

def create_zip(path, relname, archive_name):
    """
    Creates zip archive
    """
    zip = zipfile.ZipFile(archive_name, "w", zipfile.ZIP_DEFLATED)
    if os.path.isdir(path):
        zip_folder(path, relname, zip)
    else:
        kmz.write(path, relname)
    zip.close()

###############################################################################

def _(string):
    """
    Defensive method against variables not translated correctly.

    Since some strings require variables to be substituted into them, they
    need to be translated carefully. If they're not translated correctly,
    trying to do a string substitution can crash your activity.

    The code below redefines the _() to use the gettext method only if
    gettext actually works. If there is an exception, the code will simply
    return the untranslated string. This ensures that instead of crashing,
    your activity will simply not translate your string.

    @see http://wiki.laptop.org/go/Internationalization_in_Sugar
    """
    istrs_test = {}
    for i in range (0, 4):
        istrs_test[str(i)] = str(i)

    #try to use gettext. If it fails, then just return the string untranslated.
    try:
        #test translating the string with many replacements
        i = gettext(string)
#        test = i % istrs_test
#        print test
    except:
        #if it doesn't work, revert
        i = string
    return i

###############################################################################

