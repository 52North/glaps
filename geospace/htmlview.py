"""Module for embedded HTML."""
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

   ################ THIS IMPORT ORDERING IS IMPORTANT ####################

import os
import hulahop
import geospace

#hulahop.startup(os.path.join("/home/henning/olpc/workspace/GeospatialLearning/geospace/", 'gecko'))
hulahop.startup(os.path.join(geospace.BUNDLE_PATH, 'gecko'))

from hulahop.webview import WebView

   #######################################################################

import gtk
import xpcom
import logging

from xpcom import components
from xpcom.components import interfaces

from utils import _
from utils import init_logging
from geospace import GeospaceToolbar
from progresslistener import ProgressListener

DEFAULT_PAGE = os.path.join(geospace.BUNDLE_PATH, 'html/ol-template.html')
LOGGER = logging.getLogger('html-logger')
init_logging(LOGGER)

###############################################################################

class HTMLView(WebView):
    """The default view loading a map of the whole world."""

    def __init__(self, url=DEFAULT_PAGE):
        """Creates a WebViewer which embeds html into a gtk widget.

        @param url: The URL to after initializing.
        """
        WebView.__init__(self)
        self.progress = ProgressListener()

        io_service_cls = components.classes[ \
                                    "@mozilla.org/network/io-service;1"]
        weak = io_service_cls.getService(interfaces.nsIIOService) #IGNORE:W0612

        # Use xpcom to turn off "offline mode" detection, which disables
        # access to localhost for no good reason.  (Trac #6250.)
        io_service2 = io_service_cls.getService(interfaces.nsIIOService2)
        io_service2.manageOfflineStatus = False

        self.progress.connect('loading-stop', self._loaded)
        self.progress.connect('loading-progress', self._loading)

        LOGGER.debug('Loading URL %s' %url)
        self.load_uri(url)

    def do_setup(self):
        """Setup the web view client"""
        WebView.do_setup(self)
        self.progress.setup(self)
        listener = xpcom.server.WrapObject(ContentInvoker(self), \
                                            interfaces.nsIDOMEventListener)
        self.window_root.addEventListener('click', listener, False)

    def _loaded(self, progress_listener):
        """Passes post-loading processing."""
        #LOGGER.debug("page loaded.")
        pass

    def _loading(self, progress_listener, progress):
        """Passes on-loading processing."""
        #LOGGER.debug("loading %s" % progress)
        pass

    def test_cb(self, eventType, result):
        LOGGER.debug("Callback received!!!!!!!!!!!")

    def show_position(self): # XXX zoom factor as parameter here?
        """Displays the current position on the map.

        Using the GPS module the current position is retrieved, projected
        to the used projection and placed on the map as XO symbol. A
        GPS connection has to be established before.
        """
        pass

    def get_toolbar(self):
        """Method wherein a HTMLView instance can register its toolbars.

        @return: The toolbar with tools controlling this view.
        """
        return _MapToolbar()


###############################################################################

class ContentInvoker(object): #IGNORE:R0903
    """Invokes content."""
    _com_interfaces_ = interfaces.nsIDOMEventListener

    def __init__(self, browser):
        self._browser = browser

    def handleEvent(self, event): # IGNORE:C0103,R0201
        """Handles event."""
        LOGGER.debug("handle %s event" % event)

        if event.button != 2:
            return

        target = event.target
        LOGGER.debug(target.tagName.lower())

###############################################################################

class _MapToolbar(GeospaceToolbar):
    """Controller for the html view."""

    name = _('Map Tools')

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

###############################################################################

# XXX cleanup sandbox entry

class Example():

    def __init__(self):
        window = gtk.Window(gtk.WINDOW_TOPLEVEL)
        window.set_title("Drawing Area Example")
        window.connect("destroy", lambda w: gtk.main_quit())

        window.set_border_width(10)

        view = HTMLView()
        view.show()
        #event_box = GeospaceCanvas(view)
        #event_box.show()
        window.add(view)

        window.set_size_request(800, 600)
        window.show_all()

def main():
    gtk.main()
    return 0

if __name__ == '__main__':
    Example()
    main()