"""
a module to make sharing easier in Sugar Activities.
"""

import logging
import telepathy

from sugar.activity.activity import Activity, ActivityToolbox
from sugar.presence import presenceservice

from sugar.presence.tubeconn import TubeConnection
from sugar.graphics.window import Window

import gtk
import gobject

import groupthink_base as groupthink

def exhaust_event_loop():
    while gtk.events_pending():
        gtk.main_iteration()

class GroupActivity(Activity):
    """
    An abstract class for Activities using Groupthink.
    Activity authors who are writing a shared Activity should consider
    inheriting from GroupActivity instead of Sugar's standard Activity class.
    GroupActivity automates (and hides) handling of Telepathy tubes.  It also
    initializes a L{Group} and a L{TimeHandler} allowing shared activities to
    be written with minimal boilerplate.  For example, the following is a
    working shared text editor using GroupActivity::
        from groupthink import sugar_tools, gtk_tools
        import sugar
        class SharedTextDemoActivity(sugar_tools.GroupActivity):
            def initialize_display(self):
                self.cloud.textview = gtk_tools.SharedTextView()
                return self.cloud.textview
    In addition to sharing code, GroupActivity also provides subclasses with
    more informative startup screens and optionally automated save/load to the
    datastore.
    
    Caution: The methods required of a subclass of GroupActivity differ
    substantially from the methods required of a subclass of Activity.  For
    example, subclasses of GroupActivity typically do not need to implement
    a __init__ method.
    """
    
    message_preparing = "Preparing user interface"
    message_loading = "Loading object from Journal"
    message_joining = "Joining shared activity"
    
    def __init__(self, handle):
        # self.initiating indicates whether this instance has initiated sharing
        # it always starts false, but will be set to true if this activity
        # initiates sharing. In particular, if Activity.__init__ calls 
        # self.share(), self.initiating will be set to True.
        self.initiating = False
        # self._processed_share indicates whether when_shared() has been called
        self._processed_share = False
        # self.initialized tracks whether the Activity's display is up and running
        self.initialized = False
        
        self.early_setup()
        
        super(GroupActivity, self).__init__(handle)
        self.dbus_name = self.get_bundle_id()
        self.logger = logging.getLogger(self.dbus_name)
        
        self._handle = handle
        
        ##gobject.threads_init()
                
        self._sharing_completed = not self._shared_activity
        self._readfile_completed = not handle.object_id
        if self._shared_activity:
            self.message = self.message_joining
        elif handle.object_id:
            self.message = self.message_loading
        else:
            self.message = self.message_preparing

        # top toolbar with share and close buttons:
        toolbox = ActivityToolbox(self)
        self.set_toolbox(toolbox)
        toolbox.show()
        
        v = gtk.VBox()
        self.startup_label = gtk.Label(self.message)
        v.pack_start(self.startup_label)
        Window.set_canvas(self,v)
        self.show_all()
        
        # The show_all method queues up draw events, but they aren't executed
        # until the mainloop has a chance to process them.  We want to process
        # them immediately, because we need to show the waiting screen
        # before the waiting starts, not after.
        exhaust_event_loop()
        # exhaust_event_loop() provides the possibility that write_file could
        # be called at this time, so write_file is designed to trigger read_file
        # itself if that path occurs.
        
        self.tubebox = groupthink.TubeBox()
        self.timer = groupthink.TimeHandler("main", self.tubebox)
        self.cloud = groupthink.Group(self.tubebox)
        # self.cloud is extremely important.  It is the unified reference point
        # that contains all state in the system.  Everything else is stateless.
        # self.cloud has to be defined before the call to self.set_canvas, because
        # set_canvas can trigger almost anything, including pending calls to read_file,
        # which relies on self.cloud.
        
        # get the Presence Service
        self.pservice = presenceservice.get_instance()
        # Buddy object for you
        owner = self.pservice.get_owner()
        self.owner = owner

        self.connect('shared', self._shared_cb)
        self.connect('joined', self._joined_cb)
        if self.get_shared():
            if self.initiating:
                self._shared_cb(self)
            else:
                self._joined_cb(self)
        
        self.add_events(gtk.gdk.VISIBILITY_NOTIFY_MASK)
        self.connect("visibility-notify-event", self._visible_cb)
        self.connect("notify::active", self._active_cb)
        
        if not self._readfile_completed:
            self.read_file(self._jobject.file_path)
        elif not self._shared_activity:
            gobject.idle_add(self._initialize_cleanstart)
    
    def _initialize_cleanstart(self):
        self.initialize_cleanstart()
        self._initialize_display()
        return False
    
    def initialize_cleanstart(self):
        """
        Any subclass that needs to take any extra action in the case where
        the activity is launched locally without a sharing context or input
        file should override this method"""
        pass
    
    def early_setup(self):
        """
        Any subclass that needs to take an action before any external interaction
        (e.g. read_file, write_file) occurs should place that code in early_setup"""
        pass
    
    def _initialize_display(self):
        main_widget = self.initialize_display()
        Window.set_canvas(self, main_widget)
        self.initialized = True
        if self._shared_activity and not self._processed_share:
            # We are joining a shared activity, but when_shared has not yet
            # been called
            self.when_shared()
            self._processed_share = True
        self.show_all()
    
    def initialize_display(self):
        """
        All subclasses must override this method, which is the principal
        means of initializing a GroupActivity.
        @rtype: gtk.Widget
        @return: The widget that will be the display for this activity (i.e.
            the canvas)."""
        raise NotImplementedError
        
    def share(self, private=False):
        """
        The purpose of this function is solely to permit us to determine
        whether share() has been called.  This is necessary because share() may
        be called during Activity.__init__, and thus emit the 'shared' signal
        before we have a chance to connect any signal handlers."""
        self.initiating = True
        super(GroupActivity, self).share(private)
        if self.initialized and not self._processed_share:
            self.when_shared()
            self._processed_share = True
    
    def when_shared(self):
        """
        Inheritors should override this method to perform any special
        operations when the user shares the session"""
        pass

    def when_initiating_sharing(self):
        """
        Inheritors should override this method to perform any special 
        operations upon initiating sharing.  This method will not be called
        for "joiners", only for "sharers"."""
        pass

    def _shared_cb(self, activity):
        self.logger.debug('My activity was shared')
        self.initiating = True
        self._sharing_setup()

        self.logger.debug('This is my activity: making a tube...')
        id = self.tubes_chan[telepathy.CHANNEL_TYPE_TUBES].OfferDBusTube(
            self.dbus_name, {})
        self.when_initiating_sharing()

    def _sharing_setup(self):
        if self._shared_activity is None:
            self.logger.error('Failed to share or join activity')
            return

        self.conn = self._shared_activity.telepathy_conn
        self.tubes_chan = self._shared_activity.telepathy_tubes_chan
        self.text_chan = self._shared_activity.telepathy_text_chan

        self.tubes_chan[telepathy.CHANNEL_TYPE_TUBES].connect_to_signal('NewTube',
            self._new_tube_cb)

    def _list_tubes_reply_cb(self, tubes):
        self.logger.debug('Got %d tubes from ListTubes' % len(tubes))
        for tube_info in tubes:
            self._new_tube_cb(*tube_info)

    def _list_tubes_error_cb(self, e):
        self.logger.error('ListTubes() failed: %s', e)

    def _joined_cb(self, activity):
        if not self._shared_activity:
            return

        self.logger.debug('Joined an existing shared activity')
        self.initiating = False
        self._sharing_setup()

        self.logger.debug('This is not my activity: waiting for a tube...')
        self.tubes_chan[telepathy.CHANNEL_TYPE_TUBES].ListTubes(
            reply_handler=self._list_tubes_reply_cb,
            error_handler=self._list_tubes_error_cb)

    def _new_tube_cb(self, id, initiator, type, service, params, state):
        self.logger.debug('New tube: ID=%d initator=%d type=%d service=%s '
                     'params=%r state=%d', id, initiator, type, service,
                     params, state)
        if (type == telepathy.TUBE_TYPE_DBUS and
            service == self.dbus_name):
            if state == telepathy.TUBE_STATE_LOCAL_PENDING:
                self.tubes_chan[telepathy.CHANNEL_TYPE_TUBES].AcceptDBusTube(id)
            tube_conn = TubeConnection(self.conn,
                self.tubes_chan[telepathy.CHANNEL_TYPE_TUBES],
                id, group_iface=self.text_chan[telepathy.CHANNEL_INTERFACE_GROUP])
            self.tubebox.insert_tube(tube_conn, self.initiating)
            self._sharing_completed = True
            if self._readfile_completed and not self.initialized:
                self._initialize_display()

    def read_file(self, file_path):
        self.cloud.loads(self.load_from_journal(file_path))
        self._readfile_completed = True
        if self._sharing_completed and not self.initialized:
            self._initialize_display()
        pass
        
    def load_from_journal(self, file_path):
        """
        Inheritors wishing to control file saving should override this method.
        Any inheritor overriding this method must return the
        string provided to save_to_journal as cloudstring.
        The default implementation of load_from_journal simply returns the contents
        of the file, matching the default implementation of save_to_journal.
        @type file_path: str
        @param file_path: path to the file to read
        @rtype: str
        @return: a string previously passed to save_to_journal as cloudstring"""
	if file_path:
            f = file(file_path,'rb')
            s = f.read()
            f.close()
            return s
    
    def write_file(self, file_path):
        # There is a possibility that the user could trigger a write_file
        # action before read_file has occurred.  This could be dangerous,
        # potentially overwriting the journal entry with blank state.  To avoid
        # this, we ensure that read_file has been called (if there is a file to
        # read) before writing.
        if not self._readfile_completed:
            self.read_file(self._jobject.file_path)
        self.save_to_journal(file_path, self.cloud.dumps())            

    def save_to_journal(self, file_path, cloudstring):
        """Any inheritor who wishes to control file
        output should override this method, and must 
        be sure to include cloudstring in its write_file.
        The default implementation of save_to_journal simply dumps the output of 
        self.cloud.dumps() to disk.
        @type file_path: str
        @param file_path: the path to which the activity should write
        @type cloudstring: str
        @param cloudstring: an additional string representing the state of all
            objects associated with self.cloud.  This string may be saved
            as the inheritor sees fit."""
        f = file(file_path, 'wb')
        f.write(cloudstring)
        f.close()
        
    def _active_cb(self, widget, event):
        self.logger.debug("_active_cb")
        if self.props.active:
            self.resume()
        else:
            self.pause()
            
    def _visible_cb(self, widget, event):
        self.logger.debug("_visible_cb")
        if event.state == gtk.gdk.VISIBILITY_FULLY_OBSCURED:
            self.pause()
        else:
            self.resume()
    
    def pause(self):
        """
        This method will be called when the display is not visible.
        Subclasses should override this function to stop updating the display
        when it is not visible."""
        pass
    
    def resume(self):
        """
        This method will be called when the display becomes visible.
        Subclasses should override this function to resume updating the
        display, since it is now visible"""
        pass
